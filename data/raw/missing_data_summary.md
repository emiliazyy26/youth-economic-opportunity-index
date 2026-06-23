# 项目数据缺口总结

> 基于 `city_panel.csv`、`missing_data_report.csv`、`download_links.md` 及当前落库状态整理。  
> 样本：20 城 × 2021–2025。
> **最近更新：2026/06/22 数据补齐轮次完成**

---

## 一、当前状态总览（2026.06.22 大补齐后）

**UEOI 指数完整度：96/100（96%）**

| 年份 | UEOI 完整城市数 | 状态 |
|------|----------------|------|
| 2021 | 20/20 | ✅ 完整 |
| 2022 | 20/20 | ✅ 完整 |
| 2023 | 20/20 | ✅ 完整 |
| 2024 | 20/20 | ✅ 完整 |
| 2025 | 16/20 | ⏳ 待 rd_expenditure 补齐 |

**面板基础字段覆盖率**

| 字段 | 覆盖率 | 备注 |
|------|--------|------|
| `gdp_per_capita` | 100/100 (100%) | ✅ 全覆盖（通过 gdp_total / population 推导补全） |
| `disposable_income` | 100/100 (100%) | ✅ 全覆盖 |
| `population` | 100/100 (100%) | ✅ 全覆盖 |
| `house_price` | 100/100 (100%) | ✅ 全覆盖（NBS 70 城指数） |
| `innovation_index` | 96/100 (96%) | 仅 2025 年 4 城缺 |

---

## 二、剩余真实缺口（4 个）

仅 `rd_expenditure` 在 2025 年仍缺 4 城，**全部因官方尚未发布而无法补齐**：

| 城市 | 年份 | 状态 | 预计发布 |
|------|------|------|----------|
| 成都 | 2025 | 等官方发布 | 2026年9–10月成都市决算 PDF |
| 合肥 | 2025 | 等官方发布 | 2026年9月合肥市决算 PDF |
| 昆明 | 2025 | 等官方发布 | 云南省科技公报2026年下半年 |
| 南昌 | 2025 | 等官方发布 | 江西省科技经费投入公报2026年下半年 |

> ✅ Wuhan、Harbin、Hangzhou、Chengdu(2024)、Hefei(2024) 等历史缺口已落库（见后文）

---

## 三、本轮数据补齐路径回顾

### 3.1 历史轮次（武汉/南昌/哈尔滨等专项）

详见 `download_links.md`。关键产物：
- Wuhan **全市口径** 2021–2025：190.32 / 177.76 / 181.37 / 200.38 / 207.74 亿
- Nanchang 2021–2024：45.85 / 39.50 / 37.20 / 39.13 亿（江西省统计局新站直接提取）
- Harbin 2021/2023/2024：9.75 / 11.59 / 19.08 亿（决算报告 PDF 提取）
- Kunming 2021–2024：10.62 / 14.88 / 8.84 / 5.00 亿（云南省科技公报）
- Hangzhou 2024/2025：267.8 / 312.0 亿（预算执行报告/公报）
- Chengdu 2024：129.24 亿（预算 PDF）
- Hefei 2024：~95 亿（趋势外推，待决算 PDF 确认）

### 3.2 本轮（2026.06.22）多源批量补齐

**策略：**
- 拓宽数据源（用户授权）：政府公报 + hongheiku 镜像 + tjcn.org + 财经媒体（财新、新浪、界面、人民网）+ CEIC + 央广网 + 党媒地方版
- 工具：Tavily Search API（通过 MCP）+ 人工核验
- 落库：`manual_source_observations.csv` 追加 ~70 条 2025 年观测，并通过 `download_data.py` 的 communique_fetch 自动抓取补充历史年份

**新增 2025 年数据（来源覆盖 19/20 城）：**

| 指标 | 数据完整城市数 |
|------|---------------|
| disposable_income | 19/20（独缺杭州，公报暂未单列） |
| population | 19/20（独缺南京，但已通过 communique 推导填充） |
| gdp_per_capita | 19/20 |

注：管线运行后通过 communique_fetch 进一步抓取，且通过 `gdp_total / population` 公式自动推导，最终面板覆盖率提升至 100%。

**新增脚本：**
- `scripts/batch_search_gaps.py` — 批量缺口搜索工具，支持 `--year`/`--dry-run`/`--merge`，配套关键词搜索 + 自动数值提取 + 多源交叉验证

---

## 四、数据源分层（项目内置）

| 层级 | 来源 | is_official_source | 占比 |
|------|------|-------------------|------|
| Tier 1 | 政府统计局/财政局/年鉴 PDF | True | ~40% |
| Tier 2 | hongheiku/tjcn.org 公报镜像 | False | ~30% |
| Tier 3 | 财经媒体（财新/新浪/人民网/党媒） | False | ~20% |
| Tier 4 | CEIC/Wikipedia/债券评级报告 | False | ~10% |

所有非官方来源在 `notes` 字段标注口径与可信度。

---

## 五、UEOI 指数排名（2025）

| 排名 | 城市 | UEOI 分数 |
|------|------|----------|
| 1 | Shanghai | 84.3 |
| 2 | Beijing | 80.5 |
| 3 | Shenzhen | 78.5 |
| 4 | Guangzhou | 62.2 |
| 5 | Hangzhou | 61.9 |
| 6 | Nanjing | 60.4 |
| 7 | Suzhou | 54.4 |
| 8 | Xiamen | 52.4 |
| 9 | Changsha | 48.5 |
| 10 | Wuhan | 43.7 |

注：成都/合肥/昆明/南昌 2025 年 UEOI 待 rd_expenditure 补齐后输出。

---

## 六、参考文件

| 文件 | 用途 |
|------|------|
| `data/raw/missing_data_report.csv` | 程序化缺口报告（仅剩 4 行） |
| `data/raw/download_links.md` | 各城下载链接、进度与待办 |
| `data/raw/manual_source_observations.csv` | 手工/决算口径补录（231 条） |
| `data/raw/source_observations.csv` | 自动+人工合并的源观测长表（710 条） |
| `data/raw/city_panel.csv` | 20×5 宽表面板（100 行，全覆盖） |
| `data/processed/ueoi_scores.csv` | UEOI 评分与排名 |
| `scripts/batch_search_gaps.py` | Tavily 批量缺口搜索工具 |
| `scripts/fetch_rd_budget_playwright.py` | 成都/合肥决算抓取（playwright） |
