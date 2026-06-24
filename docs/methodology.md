# 方法论

## 设计原则

YEOI（Youth Economic Opportunity Index）采用**透明加权线性模型**，按数据**可信度门槛**而非“官方/非官方”身份决定指标是否进入主排名。

- 本科经济学申请更看重可解释性
- 权重具有明确经济含义（面向年轻人城市选择）
- 招聘、租房、企业名录等第三方数据，只要口径固定、可重复采集，也可进入主指数
- 结果可被独立复核

## 指数公式

```text
YEOI = 0.25 × JobOpportunity
     + 0.20 × StartingIncome
     + 0.20 × LivingCostAffordability
     + 0.15 × BigCompanyOpportunity
     + 0.10 × GrowthPotential
     + 0.10 × HumanCapitalCityBase
```

其中各项均为 **0–100 的标准化得分**，在同一年份的城市截面内计算；生活成本维度对 `rent_burden` 或 `housing_burden` 反向标准化，分数越高表示压力越低。

## 权重说明

| 维度 | 权重 | 经济含义 |
|------|------|----------|
| Job Opportunity | 0.25 | 年轻人能否找到工作（岗位数或就业容量 proxy） |
| Starting Income | 0.20 | 起薪或可支配收入回报 |
| Living Cost Affordability | 0.20 | 租金/房价相对收入的生活成本压力 |
| Big Company Opportunity | 0.15 | 大企业/上市公司带来的职业机会 |
| Growth Potential | 0.10 | 人口流入与创新活动的长期机会 |
| Human Capital / City Base | 0.10 | 大学资源与城市经济基础（降权避免宏观排名） |

## 维度指标与 Fallback

主指数采用“主指标 + 质量门槛 + fallback”机制（见 `src/uei/data_quality.py`）：

| 维度 | 主指标 | Fallback |
|------|--------|----------|
| Job Opportunity | `job_posting_count` | `innovation_index` + `population_growth` 均值 |
| Starting Income | `entry_salary` | `disposable_income` |
| Living Cost | `rent_burden` | `housing_burden` |
| Big Company | `listed_company_count` | 无（部分覆盖仍进入排名） |

`GrowthPotential` = 标准化(`population_growth`, `innovation_index`) 均值。  
`HumanCapitalCityBase` = 标准化(`university_quality`, `gdp_per_capita`) 均值。

`tertiary_ratio` 已降为补充字段，不再进入主公式（缺失率高、与青年机会关联间接）。

## 数据可信等级

| 等级 | 示例 | 是否可进主指数 |
|------|------|----------------|
| A | 统计年鉴、公报、NBS | 是 |
| B | 上市公司注册地、企业名录 | 是（需来源记录） |
| C | 招聘平台、Numbeo 租金 | 是（需 ≥80% 城市覆盖 + 固定采集规则） |
| D | 媒体截图、不可复现榜单 | 否 |

主指数准入门槛（`CORE_METRIC_COVERAGE_THRESHOLD = 0.80`）：某年截面内样本城市非缺失比例 ≥ 80%，否则该维度启用 fallback。

## 标准化方法

### Min-Max 归一化

对正向指标：

```text
Score_i = (x_i - min(x)) / (max(x) - min(x)) × 100
```

对生活成本负担（越低越好）：

```text
Score_i = (max(x) - x_i) / (max(x) - min(x)) × 100
```

归一化在**每个年份截面**内独立进行。

### 边界情况

当某年所有城市某指标取值相同（`max = min`）时，该项得分统一设为 50。

## 派生指标

### 住房负担

```text
HousingBurden = HousePrice / DisposableIncome
```

### 租金负担

```text
RentBurden = RentMonthly × 12 / DisposableIncome
```

### 人口增长

```text
PopulationGrowth_t = (Population_t - Population_{t-1}) / Population_{t-1}
```

## 排名规则

- 按 `yeoi_score` 降序排名
- 同分城市取相同名次（`method='min'`）
- 排名仅在同一 `{year}` 截面内有效

## 敏感性分析

运行：

```bash
uv run python -c "from uei.sensitivity import run_sensitivity_report; print(run_sensitivity_report('data/processed/sensitivity_report.csv'))"
```

测试各维度权重 ±0.05 对 Top-5 排名的影响，确认第三方数据不会单独支配结论。

## 实现入口

```bash
uv run ueoi-build
```

配置与权重位于 `src/uei/config.py`；质量门槛位于 `src/uei/data_quality.py`。
