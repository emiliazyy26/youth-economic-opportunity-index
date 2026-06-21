"""Fetch city-level 一般公共预算科学技术支出 from official budget pages via Playwright."""

from __future__ import annotations

import io
import json
import re
import time
from pathlib import Path

import requests
from pypdf import PdfReader
from playwright.sync_api import sync_playwright

RAW = Path("data/raw")
OUT = RAW / "_playwright_budget"
OUT.mkdir(parents=True, exist_ok=True)

ENTRY_URLS = {
    "Chengdu": [
        "https://www.chengdu.gov.cn/gkml/czyjs/column-index-1.shtml",
        "https://cdcz.chengdu.gov.cn/cdsczj/c116719/",
    ],
    "Hefei": [
        "https://czj.hefei.gov.cn/",
        "https://czj.hefei.gov.cn/czsw/bmyjs/",
        "https://www.hefei.gov.cn/c1070/index.html",
    ],
}

KEYWORDS = ("2024", "决算", "全市", "支出", "预算执行", "科学技术")


def _match_link(text: str, href: str) -> bool:
    blob = f"{text} {href}"
    return any(k in blob for k in KEYWORDS)


def browse(url: str, slug: str, wait_s: float = 15.0) -> tuple[str, str, list[dict]]:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            slow_mo=150,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.new_page()
        print(f"  goto {url}")
        page.goto(url, wait_until="networkidle", timeout=120_000)
        time.sleep(wait_s)
        html = page.content()
        title = page.title()
        links = page.eval_on_selector_all(
            "a",
            "els => els.map(e => ({text:(e.innerText||'').trim().slice(0,120), href:e.href}))",
        )
        (OUT / f"{slug}.html").write_text(html, encoding="utf-8")
        browser.close()
    return html, title, links


def extract_pdf_urls(html: str, base: str) -> list[str]:
    urls: list[str] = []
    for pat in (
        r"var pdf\s*=\s*['\"]([^'\"]+\.pdf)['\"]",
        r"href=['\"]([^'\"]+\.pdf)['\"]",
        r"attachPath\s*[:=]\s*['\"]([^'\"]+\.pdf)['\"]",
    ):
        for m in re.finditer(pat, html, re.I):
            u = m.group(1)
            if u.startswith("/"):
                from urllib.parse import urljoin

                u = urljoin(base, u)
            urls.append(u)
    return list(dict.fromkeys(urls))


def science_from_text(text: str) -> list[dict]:
    hits: list[dict] = []
    patterns = [
        r"科学技术支出[^\d]{0,30}(\d[\d,]*\.?\d*)\s*(?:万|亿)",
        r"(\d[\d,]*\.?\d*)\s*(?:万|亿)[^\n]{0,20}科学技术",
        r"206\s+科学技术[^\d]{0,40}(\d[\d,]*\.?\d*)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            raw = m.group(1).replace(",", "")
            try:
                val = float(raw)
            except ValueError:
                continue
            snippet = text[max(0, m.start() - 40) : m.end() + 40].replace("\n", " ")
            hits.append({"value_raw": val, "unit_hint": m.group(0), "snippet": snippet[:200]})
    return hits


def science_from_pdf(pdf_bytes: bytes) -> list[dict]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return science_from_text(text)


def download_pdf(url: str, dest: Path) -> bytes:
    r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    dest.write_bytes(r.content)
    return r.content


def crawl_city(city: str) -> dict:
    result: dict = {"city": city, "attempts": [], "article_hits": [], "pdf_hits": []}
    for i, url in enumerate(ENTRY_URLS[city]):
        slug = f"{city.lower()}_{i}"
        try:
            html, title, links = browse(url, slug)
        except Exception as exc:
            result["attempts"].append({"url": url, "error": str(exc)})
            continue

        attempt = {
            "url": url,
            "title": title,
            "html_len": len(html),
            "blocked": len(html) < 500 or "__jsl" in html,
            "matched_links": [],
        }
        matched = [lk for lk in links if _match_link(lk["text"], lk["href"])]
        attempt["matched_links"] = matched[:30]
        result["attempts"].append(attempt)

        if attempt["blocked"]:
            print(f"  [{city}] blocked at {url} (len={len(html)})")
            continue

        # follow top article links
        for lk in matched[:8]:
            if not any(k in lk["text"] + lk["href"] for k in ("2024", "决算", "预算执行")):
                continue
            art_slug = re.sub(r"[^\w]+", "_", lk["href"])[-60:]
            try:
                art_html, art_title, _ = browse(lk["href"], f"{slug}_art_{art_slug}", wait_s=10)
            except Exception as exc:
                result["article_hits"].append({"url": lk["href"], "error": str(exc)})
                continue

            pdfs = extract_pdf_urls(art_html, lk["href"])
            text_hits = science_from_text(art_html)
            if text_hits:
                result["article_hits"].append(
                    {"url": lk["href"], "title": art_title, "text_hits": text_hits}
                )

            for pdf_url in pdfs[:3]:
                pdf_name = OUT / f"{city.lower()}_{art_slug}.pdf"
                try:
                    pdf_bytes = download_pdf(pdf_url, pdf_name)
                    pdf_hits = science_from_pdf(pdf_bytes)
                    if pdf_hits:
                        result["pdf_hits"].append(
                            {
                                "article": lk["href"],
                                "pdf_url": pdf_url,
                                "pdf_file": str(pdf_name),
                                "hits": pdf_hits,
                            }
                        )
                except Exception as exc:
                    result["pdf_hits"].append({"pdf_url": pdf_url, "error": str(exc)})

        if i < len(ENTRY_URLS[city]) - 1:
            time.sleep(45)

    return result


def main() -> None:
    all_results = {}
    for city in ("Chengdu", "Hefei"):
        print(f"\n=== {city} ===")
        all_results[city] = crawl_city(city)
        time.sleep(60)

    out_path = OUT / "results.json"
    out_path.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    for city, res in all_results.items():
        print(city, "pdf_hits", len(res["pdf_hits"]), "article_hits", len(res["article_hits"]))


if __name__ == "__main__":
    main()
