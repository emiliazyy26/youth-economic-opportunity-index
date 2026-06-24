"""Robust per-city scraper for 2024 city-level final accounts PDFs.

Differs from fetch_rd_2024_playwright.py:
1. Persistent browser context (cookies survive across visits).
2. Longer initial settle to clear WAF challenge fully.
3. Hefei: navigate via specific final-accounts / public-accounts columns rather than monthly budget execution.
4. Chengdu: jump straight to subdomain article search after entry.
5. Saves all article HTMLs and PDF index lists for inspection.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

RAW = Path("data/raw")
OUT = RAW / "_playwright_budget"
OUT.mkdir(parents=True, exist_ok=True)
PROFILE = OUT / "_chrome_profile"
PROFILE.mkdir(parents=True, exist_ok=True)
LOG = OUT / "fetch_2024_v2.log"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------- target seeds ----------
# Use known final-accounts / public-accounts URLs from public Hefei finance pages.
HEFEI_KNOWN_SEEDS = [
    # Final accounts catalog (cat ID 4382 commonly hosts final accounts)
    "https://czj.hefei.gov.cn/public/column/4381?type=4&catId=7036479&action=list",
    "https://czj.hefei.gov.cn/public/column/4381?type=4&catId=7036478&action=list",
    # Government info disclosure -> Financial info -> Final accounts (Hefei municipal gov main site)
    "https://www.hefei.gov.cn/zwgk/zfxxgkzl/cz/czjs/",
    # Try the bureau homepage to seed cookies for the WAF
    "https://czj.hefei.gov.cn/",
]

CHENGDU_KNOWN_SEEDS = [
    # Article portal from previous successful entry
    "https://www.chengdu.gov.cn/gkml/czyjs/column-index-1.shtml",
    # Direct municipal gov financial info path
    "https://www.chengdu.gov.cn/zwgk/c126010/whcz_index.shtml",
    "https://www.chengdu.gov.cn/zwgk/c126010/index.shtml",
    # cdcz subdomain (may 403 but worth retry after profile cookies)
    "https://cdcz.chengdu.gov.cn/cdsczj/c116719/",
    "http://cdcz.chengdu.gov.cn/cdsczj/c116719/",
]


def looks_blocked(html: str) -> bool:
    if len(html) < 1500:
        return True
    if "<title>403" in html or "<title>404" in html or "Forbidden" in html[:500]:
        return True
    head = html[:2000]
    if head.count("_0x") > 5 or "var _0x" in head:
        return True
    if "_jsl_clearance" in head[:1000]:
        return True
    return False


def collect_anchors(page) -> list[dict]:
    return page.eval_on_selector_all(
        "a",
        "els => els.map(e => ({"
        "text:(e.innerText||e.textContent||'').trim().slice(0,200),"
        "href:e.href,"
        "title:e.title||''"
        "}))",
    )


def score_anchor(a: dict) -> int:
    text = a.get("text", "") + " " + a.get("title", "")
    href = a.get("href", "")
    blob = text + " " + href
    if not text.strip():
        return -10
    s = 0
    # boost final accounts context
    if "决算" in blob:
        s += 5
    if "全市" in blob:
        s += 5
    if "2024年" in blob or "2024" in blob:
        s += 4
    if "预算执行" in blob:
        s += 3
    if "预算" in blob:
        s += 1
    if "草案" in blob:
        s += 4
    if "报告" in blob:
        s += 1
    # downweight irrelevant items
    if "部门" in blob and "决算" not in blob:
        s -= 3
    monthly_patterns = [
        "1-12月", "1-11月", "1-10月", "1-9月", "1-8月",
        "1-7月", "1-6月", "1-5月", "1-4月", "1-3月", "1-2月",
    ]
    if any(k in blob for k in monthly_patterns):
        s -= 4
    if any(k in blob for k in ["招标", "中标", "采购公告", "成交", "登记"]):
        s -= 5
    if "javascript:" in href:
        s -= 5
    return s


def harvest_pdfs(html: str, base: str) -> list[str]:
    urls: list[str] = []
    for pat in (
        r"var\s+pdf\s*=\s*['\"]([^'\"]+\.pdf)['\"]",
        r"href=['\"]([^'\"]+\.pdf)['\"]",
        r"window\.open\s*\(\s*['\"]([^'\"]+\.pdf)['\"]",
        r"src=['\"]([^'\"]+\.pdf)['\"]",
    ):
        for m in re.finditer(pat, html, re.I):
            u = m.group(1)
            if not u.startswith("http"):
                u = urljoin(base, u)
            urls.append(u)
    return list(dict.fromkeys(urls))


def extract_science_tech(pdf_bytes: bytes) -> list[dict]:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        return [{"error": str(exc)}]
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    hits = []
    # Find "science & technology" with adjacent number sequences
    for m in re.finditer(r"(.{0,180}科学技术(?:支出)?.{0,200})", text):
        ctx = m.group(0).replace("\n", " | ")[:600]
        nums = re.findall(r"([\d]{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{4,})", ctx)
        if nums:
            hits.append({"context": ctx, "numbers": nums})
    return hits


def download_pdf(url: str, referer: str, dest: Path, ctx=None) -> bytes:
    headers = {"User-Agent": UA, "Referer": referer}
    # Try cookies from playwright context for the same domain
    if ctx is not None:
        cookies = ctx.cookies(url)
        if cookies:
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            headers["Cookie"] = cookie_str
    r = requests.get(url, timeout=180, headers=headers, allow_redirects=True)
    r.raise_for_status()
    dest.write_bytes(r.content)
    return r.content


def visit(page, url: str, wait_s: float = 12.0, retries: int = 1) -> tuple[str, str]:
    for attempt in range(retries + 1):
        try:
            log(f"  goto[{attempt}] {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_timeout(int(wait_s * 1000))
            html = page.content()
            title = page.title()
            if not looks_blocked(html):
                return html, title
            log(f"    blocked, retry after 8s... title={title!r} len={len(html)}")
            page.wait_for_timeout(8000)
        except Exception as exc:
            log(f"    goto error: {exc}")
            time.sleep(5)
    return "", ""


def crawl(city: str, seeds: list[str], max_articles: int = 12, max_pdfs_per_art: int = 4) -> dict:
    result: dict = {"city": city, "tried": [], "articles": [], "pdfs": [], "final": None}
    seen_urls: set[str] = set()

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE / city),
            channel="chrome",
            headless=False,
            slow_mo=80,
            user_agent=UA,
            locale="zh-CN",
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()

        queue: list[tuple[int, str]] = []

        for seed in seeds:
            html, title = visit(page, seed, wait_s=14, retries=2)
            blocked = looks_blocked(html)
            (OUT / f"v2_{city}_{re.sub(r'[^A-Za-z0-9._-]+', '_', seed)[-80:]}.html").write_text(
                html or "", encoding="utf-8"
            )
            result["tried"].append({
                "url": seed,
                "title": title,
                "html_len": len(html),
                "blocked": blocked,
            })
            if blocked or not html:
                log(f"  seed blocked: {seed}")
                continue
            anchors = collect_anchors(page)
            scored = sorted(anchors, key=score_anchor, reverse=True)
            top_score = score_anchor(scored[0]) if scored else 0
            log(f"  seed {seed} -> {len(anchors)} anchors, top score={top_score}")
            for a in scored[:25]:
                if score_anchor(a) < 4:
                    break
                href = a.get("href", "")
                if href.startswith("http") and href not in seen_urls and href not in seeds:
                    queue.append((1, href))
                    anchor_text = a['text'][:60]
                    log(f"    queued ({score_anchor(a)}): {anchor_text}  -> {href[:120]}")

        # process queue
        idx = 0
        while queue and idx < max_articles:
            depth, art = queue.pop(0)
            if art in seen_urls:
                continue
            seen_urls.add(art)
            idx += 1
            log(f"  art[{idx}/{max_articles}] depth={depth} {art}")
            html, title = visit(page, art, wait_s=8, retries=1)
            blocked = looks_blocked(html)
            entry = {
                "url": art,
                "title": title,
                "depth": depth,
                "html_len": len(html),
                "blocked": blocked,
            }
            (OUT / f"v2_{city}_art_{re.sub(r'[^A-Za-z0-9._-]+', '_', art)[-80:]}.html").write_text(
                html or "", encoding="utf-8"
            )
            result["articles"].append(entry)
            if blocked or not html:
                continue

            pdfs = harvest_pdfs(html, art)
            log(f"    found {len(pdfs)} PDF urls")
            for pdf_url in pdfs[:max_pdfs_per_art]:
                slug = re.sub(r"[^A-Za-z0-9._-]+", "_", pdf_url)[-90:]
                dest = OUT / f"v2_{city}_{slug}"
                try:
                    pdf_bytes = download_pdf(pdf_url, art, dest, ctx=ctx)
                    log(f"    dl {len(pdf_bytes)//1024}KB -> {dest.name}")
                except Exception as exc:
                    log(f"    pdf err: {exc}")
                    continue
                hits = extract_science_tech(pdf_bytes)
                strong = [h for h in hits if "context" in h and "全市" in h["context"]]
                row = {"article": art, "pdf_url": pdf_url, "pdf_file": str(dest),
                       "hits": hits, "strong": strong}
                result["pdfs"].append(row)
                if strong:
                    log(f"    ★ strong city-wide hit; first ctx: {strong[0]['context'][:200]}")

            # if no strong yet, queue interesting child links from this article
            if depth < 2 and not any(r["strong"] for r in result["pdfs"]):
                child = collect_anchors(page)
                for a in sorted(child, key=score_anchor, reverse=True)[:10]:
                    if score_anchor(a) < 5:
                        break
                    h = a.get("href", "")
                    if h.startswith("http") and h not in seen_urls:
                        queue.append((depth + 1, h))

            time.sleep(3)

        ctx.close()

    # consolidate
    for row in result["pdfs"]:
        if not row["strong"]:
            continue
        # take first strong hit, find final accounts column number heuristically
        # The final accounts column is usually the third numeric column
        # (mid-range of [budget, adjusted, final]).
        for h in row["strong"]:
            nums = h.get("numbers", [])
            # Drop year fragments like 2024
            cleaned = [n for n in nums if not re.fullmatch(r"20\d{2}", n)]
            cleaned = [n.replace(",", "") for n in cleaned]
            candidates = [float(n) for n in cleaned if re.match(r"^\d+(\.\d+)?$", n)]
            big = [c for c in candidates if c >= 10000]  # 10k yuan scale
            if not big:
                continue
            # Heuristic: pick the median of the largest credible numeric values.
            top = sorted(big)[:5]
            if len(top) >= 3:
                jusuan = sorted(top)[1]  # median-ish
            else:
                jusuan = top[0]
            yi = round(jusuan / 10000, 2)
            result["final"] = {
                "wanyuan": jusuan,
                "yiyuan": yi,
                "pdf_file": row["pdf_file"],
                "pdf_url": row["pdf_url"],
                "article": row["article"],
                "context": h["context"],
                "all_numbers": nums,
            }
            break
        if result["final"]:
            break

    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("city", choices=["chengdu", "hefei", "both"])
    args = ap.parse_args()

    results = {}
    cities = ["Chengdu", "Hefei"] if args.city == "both" else [args.city.title()]
    for city in cities:
        log(f"\n=== {city} ===")
        seeds = CHENGDU_KNOWN_SEEDS if city == "Chengdu" else HEFEI_KNOWN_SEEDS
        results[city] = crawl(city, seeds)
        if city != cities[-1]:
            log("city cooldown 30s")
            time.sleep(30)

    (OUT / "fetch_2024_v2_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for city, r in results.items():
        if r["final"]:
            log(f"  ✓ {city} city-wide science & technology expenditure final = {r['final']['yiyuan']} 100M yuan")
            log(f"    pdf: {r['final']['pdf_file']}")
        else:
            n_pdfs = len(r['pdfs'])
            n_articles = len(r['articles'])
            log(f"  ✗ {city} no strong city-wide hit; {n_pdfs} PDFs tried, {n_articles} articles")


if __name__ == "__main__":
    main()
