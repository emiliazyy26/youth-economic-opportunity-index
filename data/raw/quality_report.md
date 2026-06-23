# Data Quality Validation Report

> Generated: 2026-06-22 via `scripts/validate_observations.py`

---

## Summary

| Category | Count | Status |
|----------|-------|--------|
| Real data errors (fixed) | 6 | ✅ Fixed this round |
| Real data errors (needs manual fix) | 6 | ⚠️ Needs investigation |
| Expected / false positives | 41 | 🔵 Documented |
| Remaining `rd_expenditure` gaps | 4 | ⏳ Official data not yet published |
| **Total warnings** | **60 → effectively ~10 real issues** | |

---

## 1. Fixed This Round

| Issue | Data | Fix |
|-------|------|-----|
| Xi'an 2023 population = 4,458,800 (wrong) | communique_fetch picked wrong webpage | Manual override: 12,960,000 |
| Xi'an 2023 disposable_income = 27,047 (wrong) | communique_fetch picked wrong webpage | Manual override: 42,818 |
| Harbin 2023 GDP total = 15,760.34 亿 (wrong) | communique_fetch picked wrong webpage | Manual override: 5,576.3 亿 |
| Harbin 2023 population = 10,371,500 (wrong) | communique_fetch picked wrong webpage | Manual override: 9,395,000 |

---

## 2. Remaining Real Issues (Needs Investigation)

### 2.1 Harbin 2021 GDP inconsistency
- `gdp_per_capita` = 56,580, but `gdp_total/population × 10^8` = 12,291
- **Root cause**: `gdp_total` = 1,215.0 (unit unclear, appears wrong) from hongheiku communique
- **Impact**: None on UEOI — Harbin 2021 `gdp_score` uses `gdp_per_capita` directly
- **Fix**: Search for official Harbin 2021 communique to verify GDP total

### 2.2 Xi'an 2023 gdp_per_capita 
- `gdp_per_capita` = 53,056 from hongheiku communique (likely stale)
- `gdp_total` = 1,990.5 also from wrong communique
- **Impact**: `gdp_score` affected for Xi'an 2023
- **Fix**: Search for correct Xi'an 2023 GDP per capita

### 2.3 Harbin 2023 disposable_income spike
- 2022=41,374 → 2023=56,961 (+37.7%)
- **Root cause**: 2023 value from hongheiku communique may have different source
- **Impact**: `income_score` may be inflated for Harbin 2023
- **Fix**: Verify with official communique or CEIC

### 2.4 Kunming 2023→2024 disposable_income jump
- 2023=45,511 → 2024=57,444 (+26.2%)
- **Root cause**: 2024 value source may use different caliber (urban vs all-resident)
- **Impact**: `income_score` affected
- **Fix**: Verify both values use same income caliber

### 2.5 Chengdu 2021-2023 rd_expenditure wide-caliber issue
- 2021=237.5, 2022=250.2, 2023=268.6 → 2024=129.2 (−51.9%)
- **Root cause**: 2021-2023 use wide-caliber (R&D经费) vs 2024 narrow-caliber (科学技术支出)
- **Impact**: `innovation_score` over-estimated for Chengdu 2021-2023
- **Fix**: Replace with Chengdu budget report narrow-caliber values when available

### 2.6 Xi'an gdp_per_capita sequence
- 2022=88,806 → 2023=53,056 (−40.3%) → 2024=101,485 (+91.3%)
- **Root cause**: 2023 value questionable (wrong communique), 2024 derived from different source
- **Impact**: `gdp_score` affected
- **Fix**: Replace Xi'an 2023 gdp_per_capita with correct value

---

## 3. Expected / False Positives

### 3.1 Suzhou housing_burden ≠ NBS index
- Suzhou uses `yuan/sqm` (from 商品房销售额/销售面积) while other 19 cities use NBS 70-city index (~100)
- This is **by design** — Suzhou is NOT in the NBS 70-city list
- `housing_burden_score` uses min-max normalization within each year, so Suzhou's absolute scale doesn't affect rankings
- **Action**: None needed. Consider lowering `REASONABLE_RANGES['housing_burden']` upper bound to include Suzhou

### 3.2 Tier inversions (42 warnings)
- Nanjing/Suzhou/Hangzhou (Tier 2) exceed Guangzhou (Tier 1) in gdp_per_capita — **correct**: these are high-GDP cities
- Harbin/Kunming/Nanchang/Shenyang (Tier 3) exceed lower Tier 2 in income — **plausible**: these are provincial capitals with decent income
- **Action**: None needed. Tier classification is approximate; cross-tier overlap is expected

### 3.3 Shanghai/Shenzhen rd_expenditure > 600 亿
- Shanghai 2024=635.5, 2025=702.3; Shenzhen 2025=613.0 — **correct values**
- These are全市 narrow-caliber 科学技术支出, which are genuinely high for mega-cities
- **Action**: None needed. Raise `REASONABLE_RANGES['innovation_index']` upper bound to 800

### 3.4 Wuhan population_growth ~10%
- 2021: pop=13,648,900, growth=10.7% — likely due to 2020 census baseline correction
- **Action**: Census/administrative correction, not a data error

---

## 4. Pipeline Recommendations

1. **communique_fetch.py** incorrectly matched webpages for Xi'an 2023 and Harbin 2023
   - Add URL verification checks
   - Cross-check gdp_total, population against known ranges before accepting

2. **build_wide_panel** should also emit `gdp_per_capita` when `gdp_total + population` are both present
   - Currently works for some cities but misses when either value is from a wrong source

3. **manual_source_observations.csv** entries should include notes about caliber when different from previous years
   - Kunming 2024 disposable_income needs caliber note

---

## 5. Files

| File | Purpose |
|------|---------|
| `scripts/validate_observations.py` | Automated quality check (run with `--fix` for suggestions) |
| `data/raw/quality_report.md` | This report |
| `data/raw/manual_source_observations.csv` | Manual corrections (231 entries) |
| `data/raw/source_observations.csv` | Combined observations (710 entries) |
