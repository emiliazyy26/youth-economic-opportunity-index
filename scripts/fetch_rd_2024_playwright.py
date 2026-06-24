"""Targeted Playwright scraper for Chengdu/Hefei 2024 city-level final accounts PDF.

Strategy: open a real Chrome via Playwright, slowly navigate municipal finance bureau
sites to find the city-wide final-accounts report PDF containing the science & technology
expenditure row, download the PDF, extract the number with pypdf, and write a JSON report.

We DO NOT batch-crawl. Each city has a single seed URL list, a single browser session
with long delays (per WAF cooldown observations), and human-readable progress.

Run: uv run python scripts/fetch_rd_2024_playwright.py [chengdu|hefei|both]
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from playwright.sync_api import sync_playwright

RAW = Path("data/raw")
OUT = RAW / "_playwright_budget"
OUT.mkdir(parents=True, exist_ok=True)
PDF_DIR = RAW
LOG_FILE = OUT / "fetch_2024.log"


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------- city seeds ----------

CHENGDU_SEEDS = [
    # Public catalog entry (works per previous attempts)
    "https://www.chengdu.gov.cn/gkml/czyjs/column-index-1.shtml",
    # Municipal finance bureau jgsz_list (previous attempt got 403, retry with new session/cookie)
    "http://cdcz.chengdu.gov.cn/cdsczj/c116714/jgsz_list.shtml",
]

HEFEI_SEEDS = [
    # Municipal finance bureau -> budget execution column (depth-first start)
    "https://czj.hefei.gov.cn/czsw/czzt/ysgl/yszx/index.html",
    # Municipal finance bureau -> notices (often contains final accounts reports)
    "https://czj.hefei.gov.cn/czsw/czzt/ysgl/index.html",
    # Municipal finance bureau homepage (already works)
    "https://czj.hefei.gov.cn/",
]

KEYWORDS_INTEREST = ("2024", "决算", "预算执行", "全市", "财政", "科学技术", "草案")
# require these to bias toward city-wide final accounts (avoid departmental / monthly reports)
KEYWORDS_TARGET = ("决算", "草案", "执行情况报告")
KEYWORDS_REJECT = ("部门", "月", "代编", "招标", "采购", "中标", "成交")

PDF_NAME_HINTS = ("决算", "执行情况", "草案", "全市")

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


# ---------- pdf extraction ----------


def extract_science_tech_value(pdf_bytes: bytes) -> list[dict]:
    """Find science & technology expenditure rows with adjacent number; return all hits with context."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    hits: list[dict] = []
    # primary pattern: "...science & technology expenditure N1 N2 N3..." (final accounts table column)
    pattern = re.compile(
        r"科学技术支出\s*([\d,]+(?:\.\d+)?)(?:\s+([\d,]+(?:\.\d+)?))?"
        r"(?:\s+([\d,]+(?:\.\d+)?))?(?:\s+([\d,]+(?:\.\d+)?))?"
    )
    for m in pattern.finditer(text):
        groups = [g.replace(",", "") if g else None for g in m.groups()]
        ctx = text[max(0, m.start() - 80): m.end() + 80].replace("\n", " | ")
        hits.append({"raw_groups": groups, "context": ctx[:400]})
    return hits


def is_quanshi_caliber(context: str) -> bool:
    return "全市" in context or "全市一般公共预算" in context


# ---------- main flow ----------


def collect_links(page) -> list[dict]:
    return page.eval_on_selector_all(
        "a",
        "els => els.map(e => ({"
        "text:(e.innerText||'').trim().slice(0,150),"
        "href:e.href,"
        "title:e.title||''"
        "}))",
    )


def score_link(item: dict) -> int:
    blob = f"{item['text']} {item['href']} {item.get('title','')}"
    if not blob.strip():
        return -10
    score = 0
    for k in KEYWORDS_TARGET:
        if k in blob:
            score += 5
    for k in KEYWORDS_INTEREST:
        if k in blob:
            score += 2
    for k in KEYWORDS_REJECT:
        if k in blob:
            score -= 3
    if "2024" in blob:
        score += 3
    if "全市" in blob:
        score += 4
    if "javascript:" in item["href"]:
        score -= 5
    return score


def download_pdf(url: str, referer: str, dest: Path) -> bytes:
    headers = {"User-Agent": UA, "Referer": referer}
    r = requests.get(url, timeout=120, headers=headers)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return r.content


def harvest_pdf_urls(html: str, base: str) -> list[str]:
    urls: list[str] = []
    patterns = [
        r"var\s+pdf\s*=\s*['\"]([^'\"]+\.pdf)['\"]",
        r"href=['\"]([^'\"]+\.pdf)['\"]",
        r"attachPath\s*[:=]\s*['\"]([^'\"]+\.pdf)['\"]",
        r"window\.open\s*\(\s*['\"]([^'\"]+\.pdf)['\"]",
    ]
    for pat in patterns:
        for m in re.finditer(pat, html, re.I):
            u = m.group(1)
            if u.startswith("/"):
                u = urljoin(base, u)
            elif not u.startswith("http"):
                u = urljoin(base, u)
            urls.append(u)
    return list(dict.fromkeys(urls))


def visit(page, url: str, *, wait_s: float = 8.0) -> tuple[str, str]:
    log(f"  goto {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    except Exception as exc:
        log(f"    goto error: {exc}")
        return "", ""
    page.wait_for_timeout(int(wait_s * 1000))
    return page.content(), page.title()


def looks_blocked(html: str) -> bool:
    if len(html) < 1000:
        return True
    if "__jsl" in html or "_ts" in html and "challenge" in html.lower():
        return True
    if "<title>403" in html or "<title>404" in html or "Forbidden" in html[:500]:
        return True
    return False


def crawl_city(city: str, seeds: list[str], *, max_articles: int = 6,
               max_depth: int = 2, pdf_cap: int = 5) -> dict:
    result: dict = {"city": city, "tried": [], "candidate_articles": [],
                    "pdf_results": [], "final_value": None}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            slow_mo=120,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent=UA, locale="zh-CN",
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.new_page()

        visited_articles: set[str] = set()
        article_queue: list[tuple[int, str]] = []  # (depth, url)

        for seed in seeds:
            html, title = visit(page, seed, wait_s=10)
            seed_state = {"url": seed, "title": title, "html_len": len(html),
                          "blocked": looks_blocked(html)}
            result["tried"].append(seed_state)
            if seed_state["blocked"]:
                log(f"  blocked at {seed}, len={len(html)}")
                time.sleep(15)
                continue

            links = collect_links(page)
            scored = sorted(links, key=score_link, reverse=True)
            for lk in scored[:30]:
                if score_link(lk) <= 0:
                    break
                href = lk["href"]
                if not href.startswith("http"):
                    continue
                if href in visited_articles:
                    continue
                article_queue.append((1, href))

        # BFS articles
        idx = 0
        while article_queue and idx < max_articles:
            depth, art_url = article_queue.pop(0)
            if art_url in visited_articles:
                continue
            visited_articles.add(art_url)
            idx += 1
            log(f"  [depth={depth}] visit article ({idx}/{max_articles}): {art_url}")
            html, title = visit(page, art_url, wait_s=6)
            blocked = looks_blocked(html)
            entry = {"url": art_url, "title": title, "depth": depth,
                     "html_len": len(html), "blocked": blocked}
            result["candidate_articles"].append(entry)
            if blocked:
                time.sleep(10)
                continue

            # try PDF urls on this page
            pdfs = harvest_pdf_urls(html, art_url)
            # prefer PDF urls whose path suggests it's a final accounts doc
            pdfs_sorted = sorted(pdfs, key=lambda u: -sum(k in u for k in PDF_NAME_HINTS))
            for pdf_url in pdfs_sorted[:pdf_cap]:
                if not pdf_url.lower().endswith(".pdf"):
                    continue
                slug = re.sub(r"[^A-Za-z0-9._-]+", "_", pdf_url)[-80:]
                dest = OUT / f"{city}_{slug}"
                try:
                    pdf_bytes = download_pdf(pdf_url, art_url, dest)
                    log(f"    downloaded {len(pdf_bytes)/1024:.0f}KB {pdf_url}")
                except Exception as exc:
                    log(f"    pdf download fail: {exc}")
                    continue
                hits = extract_science_tech_value(pdf_bytes)
                strong = [h for h in hits if is_quanshi_caliber(h["context"])]
                row = {"article": art_url, "pdf_url": pdf_url,
                       "pdf_file": str(dest), "hits": hits, "strong_hits": strong}
                result["pdf_results"].append(row)
                if strong:
                    log(f"    ★ strong city-wide hit found in {dest.name}")
                    log(f"      context: {strong[0]['context']}")
                if hits and not strong:
                    log(f"    weak hits (no city-wide): {len(hits)} candidates")

            # if no PDF was useful but page mentions final accounts, try collecting sub-links for depth+1
            if depth < max_depth and not result["pdf_results"]:
                sublinks = collect_links(page)
                for lk in sorted(sublinks, key=score_link, reverse=True)[:15]:
                    if score_link(lk) <= 2:
                        break
                    if lk["href"].startswith("http") and lk["href"] not in visited_articles:
                        article_queue.append((depth + 1, lk["href"]))

            time.sleep(4)  # WAF politeness delay

        browser.close()

    # collapse to single value if any city-wide hit
    for row in result["pdf_results"]:
        if row["strong_hits"]:
            # final accounts table format: budget adjusted-budget final [completion%] [YoY%]
            grp = row["strong_hits"][0]["raw_groups"]
            # heuristically the 3rd or 2nd column is the final accounts value
            candidates = [g for g in grp if g and re.match(r"^\d+(\.\d+)?$", g)]
            if len(candidates) >= 3:
                jusuan = float(candidates[2])  # 决算数
            elif candidates:
                jusuan = float(candidates[-1])
            else:
                jusuan = None
            if jusuan is not None:
                yiyuan = round(jusuan / 10000, 2)
                result["final_value"] = {
                    "raw_wanyuan": jusuan,
                    "yiyuan": yiyuan,
                    "pdf_file": row["pdf_file"],
                    "pdf_url": row["pdf_url"],
                    "article": row["article"],
                    "context": row["strong_hits"][0]["context"],
                }
                break
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("city", nargs="?", default="both",
                    choices=["chengdu", "hefei", "both"])
    args = ap.parse_args()

    all_results: dict = {}
    cities = ["Chengdu", "Hefei"] if args.city == "both" else [args.city.title()]
    for city in cities:
        log(f"\n=== {city} ===")
        seeds = CHENGDU_SEEDS if city == "Chengdu" else HEFEI_SEEDS
        all_results[city] = crawl_city(city, seeds)
        if city != cities[-1]:
            log("city cooldown 45s")
            time.sleep(45)

    out = OUT / "fetch_2024_results.json"
    out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\nWrote {out}")
    for city, r in all_results.items():
        fv = r.get("final_value")
        if fv:
            log(f"  ✓ {city} city-wide science & technology expenditure = {fv['yiyuan']} 100M yuan (PDF: {fv['pdf_file']})")
        else:
            log(f"  ✗ {city}: no strong city-wide hit; "
                f"{len(r['pdf_results'])} PDFs tried, {len(r['candidate_articles'])} articles")


if __name__ == "__main__":
    sys.exit(main())
