# 数据设计

## 目标数据表

最终面板数据保存为 `data/processed/city_economic_opportunity.csv`。

### 字段定义

| 字段 | 类型 | 说明 | 数据等级 |
|------|------|------|----------|
| `city` | string | 城市英文名 | — |
| `year` | int | 年份 | — |
| `gdp_per_capita` | float | 人均 GDP（元） | A |
| `disposable_income` | float | 居民人均可支配收入（元） | A |
| `house_price` | float | 住房价格水平 | A/C |
| `housing_burden` | float | 住房负担 `house_price / disposable_income` | 派生 |
| `population_growth` | float | 人口同比增长率 | 派生 |
| `university_quality` | float | 大学质量加权得分 | A |
| `innovation_index` | float | R&D 经费支出 | A |
| `listed_company_count` | float | A 股上市公司注册地数量 | B |
| `job_posting_count` | float | 招聘岗位数量（平台样本） | C |
| `entry_salary` | float | 应届生/初级岗位起薪 | C |
| `rent_monthly` | float | 一居室市中心月租（元） | C |
| `rent_burden` | float | 租金负担 `rent_monthly × 12 / disposable_income` | 派生 |
| `tertiary_ratio` | float | 三产占比（**补充字段**，不进主指数） | A |

### 指数输出表

`data/processed/yeoi_scores.csv` 在原始字段基础上追加 YEOI 六维得分、`yeoi_score`、`rank` 及维度来源标签。

## 数据分层

```text
data/raw/        # source-backed 原始观测
data/interim/    # 房价指数、人口增长等派生表
data/processed/  # 清洗面板 + YEOI 分数 + 敏感性报告
```

外部青年/企业指标：

```text
data/raw/external/listed_companies_by_city.csv   # B 级
data/raw/external/youth_platform_indicators.csv  # C 级（租金、岗位、起薪）
```

缺失报告 `data/raw/missing_data_report.csv` 含 `data_tier`（A/B/C/D）与 `category`（core/supplementary）。

## 主指数数据质量门槛

- 城市覆盖率 ≥ 80%（`CORE_METRIC_COVERAGE_THRESHOLD`）方可作为主指标
- 平台数据需记录采集日期、关键词、样本规则与来源 URL
- 未达标指标自动 fallback，并在 `*_source` 字段标注

## 数据来源

### A 级：官方统计

- 国家统计局、城市统计年鉴、统计公报
- 用途：收入、GDP、人口、R&D、房价指数

### B 级：机构公开数据

- 上市公司注册地统计（`listed_companies_by_city.csv`）
- 用途：大企业机会维度

### C 级：平台样本

- Numbeo 租金（`youth_platform_indicators.csv`）
- 招聘平台岗位数/起薪（待采集；当前 fallback 至创新+人口增长、可支配收入）

### D 级：排除

- 不可复现媒体截图、口径不透明榜单

## 数据收集优先级

1. **必须（主指数 fallback 可用）：** 可支配收入、住房负担、人口增长、创新、大学质量
2. **重要（青年维度）：** 租金、上市公司数量
3. **扩展（C 级）：** 岗位数、起薪
4. **补充：** `tertiary_ratio`（不进主公式）

## 数据质量检查清单

- [ ] 20 城 × 2021–2025 面板完整
- [ ] `listed_company_count`、`rent_monthly` 已写入 source observations
- [ ] 主指数字段缺失在 missing report 中按 core/supplementary 分类
- [ ] 平台数据有 source_url 与采集说明
- [ ] `uv run ueoi-build` 可生成 `yeoi_scores.csv`
