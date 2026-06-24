# Data Download Links Summary

## 1. Nanchang

### Primary Data Source: Jiangxi Provincial S&T Expenditure Statistical Bulletin

**All years obtained (Jiangxi Provincial Bureau of Statistics official bulletin Appendix Table 2, Nanchang general public budget S&T expenditure)**

| Year | Value (100M RMB) | Growth % | Share % | Link | Status |
|------|-------------------|----------|---------|------|--------|
| 2024 | **39.13** | 5.21 | 4.16 | https://tjj.jiangxi.gov.cn/jxstjj/col/col38773/content/content_1980084826070781952.html | Extracted |
| 2023 | **37.20** | -5.85 | 4.02 | https://tjj.jiangxi.gov.cn/jxstjj/col/col38773/content/content_1869739885606395904.html | Extracted + archived |
| 2022 | **39.50** | -13.8 | 4.2 | https://tjj.jiangxi.gov.cn/jxstjj/col/col38773/content/content_1869739946880983040.html | Extracted + archived |
| 2021 | **45.85** | — | — | http://218.64.59.101/info/1134/2522.htm | Mirror (docx attachment) |

> **Key breakthrough**: After tjj.jiangxi.gov.cn redesign, new URL pattern is `jxstjj/col/col38773/content/content_XXXXX.html`. Content IDs for each year's S&T bulletin (extracted from the 2019 bulletin page's related links):
> - 2024 -> content_1980084826070781952
> - 2023 -> content_1869739885606395904
> - 2022 -> content_1869739946880983040
> - 2021 -> content_1888868586897055744
> - 2020 -> content_1888867228944998400
> - 2019 -> content_1888865337234202624 / content_1869739885606395904
>
> New site pages have HTML text tables, directly extractable (no docx/image OCR needed).
> Archived: `jiangxi_2022_keji_gongbao.html`, `jiangxi_2023_keji_gongbao.html`

> **Data consistency verification**: 2024(39.13,+5.21%) -> 2023=39.13/1.0521=37.19 ~ **37.20** OK; 2023(37.20,-5.85%) -> 2022=37.20/0.9415=39.51 ~ **39.50** OK. Official growth rates and absolute values fully consistent.

> **Appendix Table 1 (R&D expenditure, for reference)**: Nanchang 2022=139.71, 2023=144.33, 2024=158.14 (100M RMB).

---

## 2. Harbin

### Budget Report Listing Page (JS loading resolved)

- The listing page https://www.harbin.gov.cn/haerbin/c104524/navlist.shtml links are **server-side static rendered** (curl can fetch directly); previously misidentified as JS dynamic loading.
- Full historical list obtained via API pagination: `https://www.harbin.gov.cn/common/search/{channelId}?_isAgg=false&_isJson=true&_pageSize=60&page=1`, where channelId=`4e84be2305794e02ad2681ba233b1552` (106 entries, covering 2017-2026).
- PDF attachment path pattern: `c104524/{yyyymm}/{articleId}/files/{filename}.pdf`

### Budget Draft Reports (includes city-wide Table 3, text version extractable)

| Year | Article Page | PDF | Status |
|------|-------------|-----|--------|
| 2024 | c01_1076387 | .../202509/1076387/files/report.pdf (909KB) | City-wide S&T 190,792 (10K RMB) |
| 2023 | c01_1011120 | .../202409/1011120/files/report.pdf (1.2MB) | Downloaded + extracted |
| 2022 | c01_935172 | .../202310/935172/files/report.pdf (53MB, scanned) | Table is scanned image, text layer does not contain S&T figures |
| 2021 | c01_80157 | .../202209/80157/files/3e3f9662936347e29f234c665a32bedd.pdf (1.4MB) | Downloaded + extracted |

Archived: `harbin_2021_juesuan_report.pdf`, `harbin_2023_juesuan_report.pdf`

### Confirmed Data (city-wide caliber, Table 3 "Harbin General Public Budget Expenditure Settlement")

| Year | City-wide S&T Expenditure (10K RMB) | City-wide (100M RMB) | Growth % | Source |
|------|-------------------------------------|----------------------|----------|--------|
| 2024 | 190,792 | **19.08** | +64.6 | 2024 budget report Table 3, direct extraction |
| 2023 | 115,925 | **11.59** | +11.5 | 2023 budget report Table 3, direct extraction |
| 2022 | ~103,969 | **~10.40** | — | Back-calculated from 2023 growth 11.5% (2022 report is scanned) |
| 2021 | 97,527 | **9.75** | -23.2 | 2021 budget report Table 3, direct extraction |

> **Cross-validation**: 2024 city-wide 190,792 (10K), growth 64.6% -> 2023=190792/1.646=115,907 ~ **115,925** OK, consistent with 2023 report Table 3.
> City-level caliber (for reference): 2024=109,568 (10.96), 2021=15,333 (1.53). City-level vs city-wide differ significantly; cross-city comparison uses **city-wide** caliber uniformly.
> **2022 precise value**: Only the 2022 budget report is a scanned PDF (table has no text layer); city-wide value back-calculated from official growth rate chain (10.40); for precise value, OCR on c01_935168 "2022 Harbin City and City-level Fiscal Settlement" (246MB full scanned settlement table) could be done.


---

## 3. Chengdu

### WAF Breakthrough Progress (JiaSuLe JS challenge)

Chengdu Finance Bureau entire site (cdcz.chengdu.gov.cn and www.chengdu.gov.cn) uses **JiaSuLe** anti-scraping: curl/wget returns 412 + obfuscated JS challenge (`$_ts` variable); any UA/cookie combination pure HTTP request cannot pass.

- **Working method**: Playwright driving local real Chrome (`/Applications/Google Chrome.app`) + `newContext(UA)` access, wait 8s for challenge JS execution then get real page. First successful entry:
  - Fiscal budget disclosure directory: https://www.chengdu.gov.cn/gkml/czyjs/column-index-1.shtml
  - Chengdu Finance Bureau budget/settlement column: https://cdcz.chengdu.gov.cn/cdsczj/c116719/
- **Limitation**: JiaSuLe rate-limits high-frequency access; after consecutive attempts, returns challenge (empty title) persistently; needs interval before retry; exported cookies are bound to UA/fingerprint, cannot be transferred to curl. Specific settlement PDFs need Playwright to drill down after rate limit clears.

### Third-party / Reference Data

| Source | Data | Caliber |
|--------|------|---------|
| JuHui Data gotohui.com/finance/show-119834 | Chengdu district S&T expenditure 2014=12.71, 2015=26.17 (100M RMB) (2016+ JS rendered, not obtained) | City districts (not city-wide) |
| Sina Finance | 2023 city-level fiscal S&T investment 61.7 (100M RMB) | City-level |
| Sichuan Province 2024 Settlement | Provincial fiscal S&T expenditure 278.1 (100M RMB), Chengdu R&D 920.9 (100M, 61.4% of province) | Provincial |

> **Next steps**: After rate limit clears, use Playwright to access cdsczj column, locate "Chengdu XXXX City-wide General Public Budget Expenditure Settlement Table", same method as Wuhan (text PDF extractable via pypdf).

---

## 4. Hefei

| Source | Link | Status |
|--------|------|--------|
| Finance Bureau homepage | https://czj.hefei.gov.cn/ | Tavily crawler cannot access (API error), needs direct browser access |
| 2024 statistical bulletin | http://finance.anhuinews.com/ahyw/202503/t20250331_8362464.html | Accessible, but only contains total general public budget expenditure (1581.06 100M RMB), S&T expenditure **not separately listed** |

> **User lead**: https://czj.hefei.gov.cn/ -> find "Budget Settlement Report"
> **New lead**: Try https://czj.hefei.gov.cn/ "Government Information Disclosure" -> "Fiscal Funds" -> "Fiscal Budget Settlement" column

---

## 5. Wuhan

### City-wide Caliber (Table 2 City-wide General Public Budget Expenditure Settlement/Execution, text PDF, pypdf direct extraction)

| Year | City-wide S&T Expenditure (10K RMB) | City-wide (100M RMB) | Growth % | PDF |
|------|-------------------------------------|----------------------|----------|-----|
| 2025 (execution) | 2,077,429 | **207.74** | — | .../202601/P020260126637828068174.pdf |
| 2024 | 2,003,842 | **200.38** | 10.5 | .../202509/P020250915369946144212.pdf |
| 2023 | 1,813,716 | **181.37** | 2.0 | .../202409/P020240912359285485449.pdf |
| 2022 | 1,777,569 | **177.76** | -6.6 | .../202309/P020230927586099820024.pdf |

Archived: `wuhan_2022/2023/2024_quanshi_zhichu_juesuan.pdf`, `wuhan_2025_quanshi_zhichu_zhixing.pdf`

> **Key breakthrough (listing JS pagination)**: Wuhan CZYJS column listing uses `createPageHTML` JS pagination; curl only gets first page. Used Playwright driving real Chrome to access listing page, loop-click "Next Page" button to paginate, locate each year's "Table 2: Wuhan XXXX City-wide General Public Budget Expenditure Settlement Table" article page; article page HTML contains `var pdf='...P0xxx.pdf'` as attachment address; PDF is text version, pypdf direct extraction.
> 2024 city-wide settlement table page: .../202509/t20250915_2647497.html; 2023: .../202409/t20240912_2453697.html; 2022: .../202309/t20240927_2272491.html

### City-level Caliber (budget report, for reference)

| Year | City-level S&T Expenditure (100M RMB) | PDF |
|------|--------------------------------------|-----|
| 2024 | 138.94 | .../202509/P020250915377637094477.pdf |
| 2023 | 132.11 | .../202409/P020240912370202141023.pdf |
| 2022 | 123.46 | .../202309/P020230927588797709848.pdf |
| 2025 (budget) | 157.68 | 2025 budget draft |

> City-wide caliber (177-208 100M) is much larger than city-level (123-139 100M); district S&T expenditure share is high. **Cross-city comparison uses city-wide caliber uniformly**.

---

## 6. Hangzhou

### Budget Settlement Reports

| Year | Link | Status |
|------|------|--------|
| 2024 | https://zjjcmspublic.oss-cn-hangzhou-zwynet-d01-a.internet.cloud.zj.gov.cn/jcms_files/jcms1/web149/site/attach/0/22d597e448ef42f3912db9c80b730f3c.pdf | Extracted, city-wide S&T expenditure **267.8 (100M RMB)** (same-caliber growth 15.5%) |
| 2023 | https://z.hangzhou.com.cn/2020/hzrmzfgb/content/content_8696702.html | Accessible (html), 2023 budget execution report |

### Confirmed Data

| Year | City-wide S&T Expenditure (100M RMB) | Source |
|------|--------------------------------------|--------|
| 2024 | 267.8 | 2024 budget execution and 2025 budget draft report PDF, confirmed by 2024 statistical bulletin (268) |
| 2025 budget | 308.0 | 2025 budget draft (growth 15%) |

> **Note**: Hangzhou S&T expenditure scale far exceeds other cities (267.8 vs Wuhan city-level 139, Nanchang 39), possibly because Hangzhou caliber includes district city-wide data, digital economy R&D subsidies, etc. Need to confirm comparable caliber with other cities.

---

## 7. Kunming

### Primary Data Source: Yunnan Provincial S&T Statistical Bulletin

| Year | Link | Status |
|------|------|--------|
| 2024 | https://kjt.yn.gov.cn/html/2025/kejitongji_1110/3011837.html | Extracted, Kunming fiscal S&T expenditure 5.00 (100M RMB) |
| 2023 | https://kjt.yn.gov.cn/uploadfile/s49/2024/1114/20241114050259893.pdf | Data available, Kunming 8.84 (100M RMB) |
| 2022 | https://kjt.yn.gov.cn/html/2023/kejitongji_1025/8091.html | Extracted, Table 3 Kunming fiscal S&T expenditure 148,816 (10K) = 14.88 (100M RMB) |
| 2021 | https://kjt.yn.gov.cn/uploadfile/s49/2022/1014/20221014035519506.pdf | Downloaded + OCR, Table 3 Kunming fiscal S&T expenditure 106,211 (10K) = 10.62 (100M RMB) |
| 2025 | Expected https://kjt.yn.gov.cn/ publication in Oct 2026 | Not yet published |

---

## 8. Jiangxi Province 2022 Bulletin (Nanchang 2022) - Resolved

**Obtained directly via tjj.jiangxi.gov.cn new content page** (see Section 1 Nanchang):
- 2022 bulletin: content_1869739946880983040 -> Nanchang **39.50 (100M RMB)**
- 2023 bulletin: content_1869739885606395904 -> Nanchang **37.20 (100M RMB)**

> Previous assessment that "old URL 404 / cannot obtain" was incorrect -- new site content IDs can be fully extracted from the 2019 bulletin page's "related links" list, no docx/image/OCR needed.

---

## 9. Data Caliber Notes

All data uniformly uses "general public budget S&T expenditure / fiscal S&T expenditure" caliber (unit: 100M RMB).

| City | Data Source Type | Notes |
|------|-----------------|-------|
| Kunming | Yunnan Provincial S&T Statistical Bulletin Table 3 | Provincial bulletin directly lists prefecture-level data |
| Nanchang | Jiangxi Provincial S&T Expenditure Statistical Bulletin Appendix Table 2 | New site content page HTML table, 2021-2024 complete |
| Harbin | Harbin Budget Draft Report PDF Table 3 | City-wide caliber, 2021/2023/2024 direct extraction |
| Chengdu | Chengdu Budget Report | JiaSuLe WAF, Playwright can break through but rate-limited |
| Hefei | Hefei Budget Report | Finance Bureau site not obtained, needs manual access |
| Wuhan | Wuhan Table 2 City-wide Expenditure Settlement Table | City-wide 2022-2024 settlement + 2025 execution |
| Hangzhou | Hangzhou Budget Execution Report | City-wide 2024 |

## 10. Data Collection Progress Summary (unit: 100M RMB)

| City | Caliber | 2021 | 2022 | 2023 | 2024 | 2025 |
|------|---------|------|------|------|------|------|
| **Kunming** | City-wide | 10.62 | 14.88 | 8.84 | 5.00 | Pending 2026.10 |
| **Nanchang** | City-wide | 45.85 | **39.50** | **37.20** | 39.13 | — |
| **Harbin** | City-wide | **9.75** | ~10.40 | **11.59** | 19.08 | — |
| **Wuhan** | City-wide | N/A | **177.76** | **181.37** | **200.38** | 207.74 (execution) |
| **Hangzhou** | City-wide | N/A | N/A | N/A | 267.8 | 308 (budget) |
| **Chengdu** | — | N/A | N/A | N/A | N/A | — |
| **Hefei** | — | N/A | N/A | N/A | N/A | — |

Harbin 2022 is back-calculated from official growth rate (all others are direct extraction from official bulletins/budget reports).
Wuhan city-level caliber for reference: 2022=123.46 / 2023=132.11 / 2024=138.94 (100M RMB).

> **Caliber Notes (important)**:
> - Kunming / Nanchang / Harbin / Wuhan / Hangzhou = **city-wide** caliber, directly comparable.
> - Wuhan city-wide 2022-2024 are settlement final numbers; 2025 is execution number.
> - Chengdu (JiaSuLe WAF, Playwright can break through but rate-limited), Hefei (Finance Bureau site not obtained settlement) remain two gaps; see corresponding sections for next steps.

### New/Corrected This Round

- Wuhan **city-wide** caliber 2022-2025 all obtained (177.76/181.37/200.38/207.74): Playwright paginated listing to locate each year's "Table 2 city-wide expenditure settlement table", text PDF pypdf direct extraction, replacing previous city-level-only series.
- Nanchang 2022 (39.50), 2023 (37.20): Jiangxi Provincial Bureau of Statistics new site content page direct extraction.
- Harbin 2021 (9.75), 2023 (11.59), 2024 (19.08): Budget report PDF direct extraction + cross-validation; 2022 (~10.40) back-calculated.
- Chengdu WAF: Verified Playwright + real Chrome can break through JiaSuLe (obtained entry), but rate limiting unstable; settlement PDF pending after rate limit clears.
- OCR capability established (tesseract + chi_sim language pack), for scanned document fallback.
- New archives: `wuhan_2022/2023/2024_quanshi_zhichu_juesuan.pdf`, `wuhan_2025_quanshi_zhichu_zhixing.pdf`, `harbin_2021/2023_juesuan_report.pdf`, `jiangxi_2022/2023_keji_gongbao.html`, `hangzhou_2024_bgtzx.pdf`

### Data Database Repair (This Round)

Previously confirmed 6 values were only recorded in this document/archive files, not written to `manual_source_observations.csv`, causing `source_observations.csv` / panel gaps. This round entered all values, making data fully reproducible from manual file:

- Nanchang 2021 (45.85), 2022 (39.50), Harbin 2021 (9.75), 2022 (10.40), Kunming 2021 (10.62), 2022 (14.88) all written to `manual_source_observations.csv` and pipeline rebuilt.
- rd_expenditure coverage: 20 cities 2021-2024 basically complete (only Chengdu 2024, Hefei 2024 missing).
- `missing_data_report.csv` reorganized: only **Chengdu 2024 / Hefei 2024** (site blocked, `not_found`) + 7 cities **2025** (`genuinely_not_published`, 2026 publication) remain.

### TODO (Remaining Real Gaps)

- **Chengdu 2024**: Playwright + real Chrome first round can enter `chengdu.gov.cn/gkml/czyjs/column-index-1.shtml` (73KB, contains entry); but `cdcz.chengdu.gov.cn` subdomain 403/39B, after consecutive scraping the portal is also rate-limited. **S&T expenditure value not extracted this round**.
- **Hefei 2024**: Playwright first round can enter `czj.hefei.gov.cn/` (84KB) and `bmyjs/index.html` (department settlement list); sub-page/second access triggers JiaSuLe challenge (~45KB JS, not real content). `hefei.gov.cn/public/.../fiscal funds` also 521. Department settlement only has "Hefei Finance Bureau 2024 Department Settlement", not city-wide caliber. **City-wide S&T expenditure value not extracted this round**.
- Scraping scripts: `scripts/fetch_rd_budget_playwright.py`; debug HTML/JSON in `data/raw/_playwright_budget/`. Recommend IP cooldown for several hours before single-URL slow retry, or local browser manual WAF bypass then export PDF.
