"""从各城市统计局官网抓取统计公报数据。"""

from __future__ import annotations

import io
import re
import time
from html import unescape
from urllib.parse import urljoin

import pandas as pd
import requests
from pypdf import PdfReader

from yei.communique_manifest import COMMUNIQUE_MANIFEST, SSL_VERIFY_EXEMPT_HOSTS
from yei.communique_ocr import (
    metrics_need_ocr,
    normalize_ocr_text,
    ocr_html_images,
    page_needs_ocr,
)
from yei.communique_sources import COMMUNIQUE_SOURCE_BY_CITY
from yei.config import ALL_CITIES, YEARS

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
)

_NC_REFERER = "http://www.nc.gov.cn/"

_FOOTNOTE_MARKER = r"(?:\s*(?:\[\d+\]|［\d+］))*"

# 主 URL 无法覆盖全部指标时，按顺序补充抓取并合并。
SUPPLEMENTARY_COMMUNIQUE_URLS: dict[tuple[str, int], tuple[str, ...]] = {
    (
        "Nanchang",
        2023,
    ): (
        "https://www.nc.gov.cn/ncszf/sjfb/202501/07af535d648c42ea95b322c191e6c175.shtml",
    ),
    (
        "Nanchang",
        2024,
    ): (
        "https://www.nc.gov.cn/ncszf/sjfb/202502/4e66745eb31e4ca4bd6bbddc560c9567.shtml",
    ),
    (
        "Nanchang",
        2025,
    ): (
        "https://www.nc.gov.cn/ncszf/sjfb/202502/4e66745eb31e4ca4bd6bbddc560c9567.shtml",
    ),
}


def _clean_html(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text)


def _fetch_bytes(url: str, timeout: int = 30) -> tuple[bytes, str]:
    if url.startswith("https://") and any(host in url for host in SSL_VERIFY_EXEMPT_HOSTS):
        url = "http://" + url.removeprefix("https://")
    verify = not any(host in url for host in SSL_VERIFY_EXEMPT_HOSTS)
    headers = {}
    if "tjj.nc.gov.cn" in url or "nc.gov.cn" in url:
        headers["Referer"] = _NC_REFERER
    response = SESSION.get(url, timeout=timeout, verify=verify, headers=headers or None)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    return response.content, content_type


def _fetch(url: str, timeout: int = 30) -> str:
    content, _ = _fetch_bytes(url, timeout=timeout)
    return content.decode("utf-8", errors="replace")


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return " ".join(page.extract_text() or "" for page in reader.pages)


def _extract_pdf_link(html: str, base_url: str) -> str | None:
    for href, title in _extract_links(html):
        if "统计公报" not in title and "统计公报" not in href:
            continue
        if href.lower().endswith(".pdf"):
            return urljoin(base_url, href)
    pdf_match = re.search(r'href="([^"]+\.pdf)"', html, flags=re.I)
    if pdf_match:
        return urljoin(base_url, unescape(pdf_match.group(1)))
    return None


def _fetch_page(url: str) -> tuple[str, str]:
    content, content_type = _fetch_bytes(url)
    if url.lower().endswith(".pdf") or "pdf" in content_type.lower():
        return "", _extract_pdf_text(content)

    html = content.decode("utf-8", errors="replace")
    text = _clean_html(html)
    pdf_url = _extract_pdf_link(html, url)
    if pdf_url and (len(text.strip()) < 2000 or not text.strip()):
        pdf_content, pdf_type = _fetch_bytes(pdf_url)
        if pdf_url.lower().endswith(".pdf") or "pdf" in pdf_type.lower():
            return "", _extract_pdf_text(pdf_content)

    if text.strip():
        return html, text

    if pdf_url:
        pdf_content, pdf_type = _fetch_bytes(pdf_url)
        if pdf_url.lower().endswith(".pdf") or "pdf" in pdf_type.lower():
            return "", _extract_pdf_text(pdf_content)
    return html, text


def _fetch_document_text(url: str) -> str:
    _, text = _fetch_page(url)
    return text


def _list_base_url(list_url: str) -> str:
    if list_url.endswith((".html", ".htm", ".shtml", ".jhtml")):
        return f"{list_url.rsplit('/', 1)[0]}/"
    return list_url if list_url.endswith("/") else f"{list_url}/"


def _extract_links(html: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for match in re.finditer(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", html, flags=re.I | re.S):
        href = unescape(match.group(1)).strip()
        anchor_html = match.group(0)
        title_match = re.search(r"\btitle=\"([^\"]+)\"", anchor_html, flags=re.I)
        title = _clean_html(match.group(2)).strip()
        if not title and title_match:
            title = unescape(title_match.group(1)).strip()
        if href and title:
            links.append((href, title))
    return links


def discover_communique_url(city: str, year: int) -> str | None:
    source = COMMUNIQUE_SOURCE_BY_CITY[city]
    year_text = f"{year}年"
    publish_year = year + 1

    for list_url in source.list_urls:
        try:
            html = _fetch(list_url)
        except Exception:
            continue

        candidates: list[tuple[int, str]] = []
        for href, title in _extract_links(html):
            if "解读" in title or "评读" in title:
                continue
            if "统计公报" not in title and "统计公报" not in href:
                continue
            if "国民经济和社会发展" not in title and str(year) not in title:
                continue
            if year_text not in title and f"{year}年" not in title:
                continue

            base = _list_base_url(list_url)
            full_url = urljoin(base, href)
            score = 0
            if "国民经济和社会发展统计公报" in title:
                score += 20
            if year_text in title:
                score += 10
            if f"/{publish_year}03/" in full_url or f"/{publish_year}04/" in full_url:
                score += 5
            if full_url.lower().endswith(".pdf"):
                score -= 15
            candidates.append((score, full_url))

        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]

    return None


_OCR_GDP_TOTAL_PATTERN = r"地区生产总值(?:\(GDP\)|（GDP）)?[^0-9]{0,12}(\d+(?:\.\d+)?)\s*亿元"


def _gdp_total_patterns() -> list[str]:
    return [
        rf"(?:全年)?(?:实现)?(?:全市)?地区生产总值(?:\(GDP\)|（GDP）)?"
        rf"{_FOOTNOTE_MARKER}"
        rf"(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*亿元",
        rf"(?:全市)?地区生产总值(?:\(GDP\)|（GDP）)?"
        rf"{_FOOTNOTE_MARKER}"
        rf"(?:突破[^，,；;]*?[，,；;])?(?:达到|为)?\s*(\d+(?:\.\d+)?)\s*亿元",
        _OCR_GDP_TOTAL_PATTERN,
        r"全年地区生产总值(?:\(GDP\)|（GDP）)?\s*(\d+(?:\.\d+)?)\s*亿元",
        r"全市地区生产总值\s*(\d+(?:\.\d+)?)\s*亿元",
        r"地区生产总值\s*(\d+(?:\.\d+)?)\s*亿元",
    ]


def _population_text_matches_year(text: str, year: int) -> bool:
    if re.search(rf"{year}年末", text):
        return True
    if re.search(rf"{year - 1}年末", text) and not re.search(rf"{year}年末", text):
        return False
    return True


def _estimate_combined_income(text: str) -> float | None:
    urban_match = re.search(
        r"城镇(?:常住)?居民人均可支配收入(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*元",
        text,
    )
    rural_match = re.search(
        r"农村(?:常住)?居民人均可支配收入(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*元",
        text,
    )
    rate_match = re.search(r"城镇化率[^0-9]*(\d+(?:\.\d+)?)\s*%", text)
    if not urban_match or not rural_match or not rate_match:
        return None
    urban_share = float(rate_match.group(1)) / 100
    urban = float(urban_match.group(1))
    rural = float(rural_match.group(1))
    return urban * urban_share + rural * (1 - urban_share)


def parse_communique_metrics(text: str, year: int | None = None) -> dict[str, float]:
    text = normalize_ocr_text(re.sub(r"\s+", " ", text))
    metrics: dict[str, float] = {}
    population_allowed = year is None or _population_text_matches_year(text, year)

    gdp_patterns = [
        r"人均地区生产总值(?:为|达到|达)?\s*(\d+(?:\.\d+)?)\s*万元",
        r"人均地区生产总值(?:为|达到|达)?\s*(\d+(?:\.\d+)?)\s*元",
        r"人均\s*GDP[^。]{0,120}?(\d+(?:\.\d+)?)\s*元",
    ]
    for pattern in gdp_patterns:
        gdp_match = re.search(pattern, text)
        if gdp_match:
            value = float(gdp_match.group(1))
            metrics["gdp_per_capita"] = value * 10000 if "万元" in pattern else value
            break

    income_patterns = [
        r"全体居民(?:实现)?人均可支配收入(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*元",
        r"全市居民人均可支配收入(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*元",
        r"全年居民人均可支配收入(?:\[.*?\])?\s*(\d+(?:\.\d+)?)\s*元",
        r"(?<!城镇)(?<!农村)(?<!城乡)居民人均可支配收入(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*元",
    ]
    for pattern in income_patterns:
        income_match = re.search(pattern, text)
        if income_match:
            metrics["disposable_income"] = float(income_match.group(1))
            break

    population_patterns = [
        r"年末(?:全市|全市域)?常住人口(?:\[.*?\])?\s*(\d+(?:\.\d+)?)\s*万人",
        r"截至\d{4}年末[,，]?\s*全市常住人口(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*万人",
        r"年末(?:全市)?常住总人口(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*万人",
        r"年末全市户籍总人口(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*万人",
        r"(?<!城镇)常住人口(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*万(?:人)?",
    ]
    if population_allowed and year == 2023:
        prior_year_pop = re.search(
            r"常住人口\s*(\d+(?:\.\d+)?)\s*万人\s*[，,]\s*比上年末\s*增加\s*(\d+(?:\.\d+)?)\s*万人",
            text,
        )
        if prior_year_pop:
            end_population = float(prior_year_pop.group(1)) - float(prior_year_pop.group(2))
            metrics["population"] = end_population * 10000

    if population_allowed and "population" not in metrics:
        for pattern in population_patterns:
            population_match = re.search(pattern, text)
            if population_match:
                metrics["population"] = float(population_match.group(1)) * 10000
                break

    innovation_patterns = [
        r"研究与试验发展(?:\(R&D\))?经费(?:支出)?(?:为)?\s*(\d+(?:\.\d+)?)\s*亿元",
        r"R&D经费(?:支出)?(?:为)?\s*(\d+(?:\.\d+)?)\s*亿元",
        r"科学技术支出(?:为)?\s*(\d+(?:\.\d+)?)\s*亿元",
    ]
    for pattern in innovation_patterns:
        innovation_match = re.search(pattern, text)
        if innovation_match:
            metrics["rd_expenditure"] = float(innovation_match.group(1))
            break

    if year is not None:
        revised_gdp_match = re.search(
            rf"{year}年(?:南昌)?地区生产总值修订为\s*(\d+(?:\.\d+)?)\s*亿元",
            text,
        )
        if revised_gdp_match:
            metrics["gdp_total"] = float(revised_gdp_match.group(1))

    if "gdp_total" not in metrics:
        for pattern in _gdp_total_patterns():
            gdp_total_match = re.search(pattern, text)
            if gdp_total_match:
                metrics["gdp_total"] = float(gdp_total_match.group(1))
                break

    # 第三产业：优先提取结构占比，备选提取绝对值
    tertiary_ratio_match = re.search(
        r"三次产业(?:增加值)?结构(?:为)?\s*[\d.]+\s*[：:]\s*[\d.]+\s*[：:]\s*([\d.]+)",
        text,
    )
    if tertiary_ratio_match:
        metrics["tertiary_ratio"] = float(tertiary_ratio_match.group(1))
    else:
        tertiary_value_match = re.search(
            r"第三产业增加值(?:为|达到)?\s*(\d+(?:\.\d+)?)\s*亿元",
            text,
        )
        if tertiary_value_match:
            metrics["tertiary_value"] = float(tertiary_value_match.group(1))

    return metrics


def resolve_communique_url(city: str, year: int) -> str | None:
    manifest_url = COMMUNIQUE_MANIFEST.get((city, year))
    if manifest_url:
        return manifest_url
    return discover_communique_url(city, year)


def _finalize_derived_metrics(
    metrics: dict[str, float],
    text: str,
    year: int | None,
) -> dict[str, float]:
    """保留可直接核验的总量，不在 source 层派生人均值。"""
    if "gdp_total" in metrics:
        return metrics

    if year is not None:
        revised_gdp_match = re.search(
            rf"{year}年(?:南昌)?地区生产总值修订为\s*(\d+(?:\.\d+)?)\s*亿元",
            text,
        )
        if revised_gdp_match:
            metrics["gdp_total"] = float(revised_gdp_match.group(1))
            return metrics

    for pattern in _gdp_total_patterns():
        gdp_total_match = re.search(pattern, text)
        if gdp_total_match:
            metrics["gdp_total"] = float(gdp_total_match.group(1))
            break

    return metrics


def _merge_metrics(base: dict[str, float], extra: dict[str, float]) -> dict[str, float]:
    merged = dict(base)
    for key, value in extra.items():
        if key not in merged:
            merged[key] = value
    return merged


def fetch_city_year(city: str, year: int) -> dict | None:
    url = resolve_communique_url(city, year)
    if not url:
        return None

    try:
        html, text = _fetch_page(url)
    except Exception:
        return None

    metrics = parse_communique_metrics(text, year=year)
    combined_text = text
    for supplement_url in SUPPLEMENTARY_COMMUNIQUE_URLS.get((city, year), ()):
        try:
            supplement_text = _fetch_document_text(supplement_url)
        except Exception:
            continue
        combined_text = f"{combined_text} {supplement_text}"
        metrics = _merge_metrics(
            metrics,
            parse_communique_metrics(supplement_text, year=year),
        )

    if html and metrics_need_ocr(metrics) and page_needs_ocr(html, text):
        try:
            ocr_text = normalize_ocr_text(ocr_html_images(html, url, _fetch_bytes))
        except Exception:
            ocr_text = ""
        if ocr_text.strip():
            combined_text = f"{combined_text} {ocr_text}"

    combined_metrics = parse_communique_metrics(combined_text, year=year)
    metrics = _merge_metrics(combined_metrics, metrics)
    metrics = _finalize_derived_metrics(metrics, combined_text, year)

    if not metrics:
        return None

    return {
        "city": city,
        "year": year,
        **metrics,
        "source": "City statistical communique",
        "source_url": url,
    }


def fetch_communique_panel(
    years: list[int] | None = None,
    sleep_seconds: float = 0.3,
) -> pd.DataFrame:
    target_years = years or (YEARS + [2020])
    records: list[dict] = []

    for city in ALL_CITIES:
        for year in target_years:
            try:
                record = fetch_city_year(city, year)
            except Exception:
                record = None
            if record:
                records.append(record)
            time.sleep(sleep_seconds)

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).sort_values(["city", "year"]).reset_index(drop=True)
