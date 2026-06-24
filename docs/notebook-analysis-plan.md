# Notebooks 分析规划

本文档说明 `notebooks/` 目录下各 notebook 的定位、分析顺序与产出目标，与 [project-design.md](project-design.md) 中的研究问题和方法论保持一致。

## 1. 总体原则

`notebooks/` 承担**研究叙事线**，不是生产流水线。可复现的计算逻辑放在 `src/yei/`；notebook 负责展示：

- 数据从哪来、是否可信
- 城市之间有什么模式
- 指数如何解释
- 结论是否稳健

推荐分析主线：

```text
数据可信度 → 指标分布 → 收入与住房压力的权衡 → YEOI 排名 → 分组解释与稳健性 → 结论
```

Notebook 顺序：

```text
01_data_sources.ipynb
→ 02_data_cleaning.ipynb
→ 03_exploratory_analysis.ipynb
→ 04_index_calculation.ipynb
→ 05_explanatory_model.ipynb
```

运行前需先完成数据准备：

```bash
uv run yeoi-download
uv run yeoi-build
```

Notebook 主要读取：

| 文件 | 用途 |
|------|------|
| `data/raw/city_panel.csv` | 原始宽表面板 |
| `data/raw/source_observations.csv` | 逐条观测与来源 |
| `data/raw/data_sources.csv` | 来源汇总 |
| `data/raw/missing_data_report.csv` | 缺口报告 |
| `data/processed/city_economic_opportunity.csv` | 清洗后面板 |
| `data/processed/yeoi_scores.csv` | 分项得分与排名 |

---

## 2. 各 Notebook 规划

### 01 Data Sources — 数据能不能信

**目标**：建立样本与来源的可信度说明。

**建议内容**：

- 20 城 × 2021–2025 样本设计
- 城市分组：超大城市、强二线、转型成长、对照组（见 `src/yei/config.py` 中 `CITIES`）
- 汇总 `source_observations.csv`、`data_sources.csv` 的来源类型
- 统计官方来源、第三方镜像、手工补录的比例
- 展示 `missing_data_report.csv`，说明当前主要缺口为 `rd_expenditure`
- 明确 `innovation_index = rd_expenditure` 的口径与局限

**核心输出**：

- 城市分组表
- 各指标覆盖率表
- 来源类型占比
- 缺失数据清单

**篇幅**：保持简洁，服务于「数据可信、流程可复现」。

---

### 02 Data Cleaning — 数据如何变成可分析面板

**目标**：说明从原始观测到分析面板的转换过程。

**建议内容**：

- 读取 `data/raw/city_panel.csv`，验证行数为 100（20 城 × 5 年）
- 核心字段缺失检查
- 展示衍生字段：
  - `population_growth`（由人口序列计算）
  - `housing_burden`（房价指数 / 可支配收入）
  - `innovation_index`（当前等于 `rd_expenditure`）
- 说明项目原则：不做 proxy、不随意估算，只保留 source-backed 数据
- 对缺失值做**解释**，而非强行填补

**实现说明**：权威清洗逻辑在 `src/yei/clean_data.py` 与 `src/yei/download_data.py`；本 notebook 以解释与验证为主，不必重复实现大量清洗代码。

**核心输出**：

- 缺失值表或热力图
- 字段单位与口径说明
- 2021–2025 各年覆盖率

---

### 03 Exploratory Analysis — 探索性分析（优先完善）

**目标**：回答 [project-design.md](project-design.md) 中的三个经济学问题：

1. 高收入城市是否仍然值得承受更高住房成本？
2. 住房压力是否会抵消城市提供的经济机会？
3. 哪些城市具有更好的长期吸引力和增长潜力？

**建议分析**：

- 最新年份收入排名（`disposable_income`）
- 最新年份住房压力排名（`housing_burden`，越高压力越大）
- 人均 GDP 与可支配收入对比
- 收入 vs 住房负担散点图（可按城市组着色）
- 人口增长时间趋势（`population_growth`）
- 创新指标时间趋势（`innovation_index`）
- 城市分组箱线图

**核心图表（对应 project-design 第 8 节）**：

| 序号 | 图表 | 变量 |
|------|------|------|
| 1 | 收入排名 | `disposable_income` |
| 2 | 住房负担排名 | `housing_burden` |
| 3 | 人均 GDP 对比 | `gdp_per_capita` |
| 4 | 人口增长变化 | `population_growth` |
| 5 | （可选）收入 vs 住房负担散点 | 两变量 + 城市组 |

**经济解释方向**：

- 一线城市：收入高，住房压力也高
- 部分强二线：收入与住房压力之间可能更平衡
- 人口增长：区分「高收入但吸引力下降」与「收入中等但增长强」的城市

**优先级**：本 notebook 最能产出图表与故事线，应**优先完善**。

---

### 04 Index Calculation — YEOI 如何计算、排名是否合理

**目标**：透明展示指数构建与排名结果。

**建议内容**：

- 同一年份截面 Min-Max 标准化（见 [methodology.md](methodology.md)）
- 五个分项得分：
  - `income_score`
  - `gdp_score`
  - `population_growth_score`
  - `innovation_score`
  - `housing_burden_score`（**越高表示住房可负担性越好**）
- 权重与综合得分
- 最新年份 YEOI 排名
- 2021–2025 排名变化
- Top 城市分项对比（雷达图或 stacked bar）

**指数公式（与代码一致）**：

代码中 `housing_burden_score` 已反向标准化，分数越高表示住房压力越低，因此：

```text
YEOI = 0.25 × IncomeScore + 0.20 × GDPScore + 0.15 × TalentCapitalScore
     + 0.12 × PopulationGrowthScore + 0.12 × InnovationScore
     + 0.10 × IndustryStructureScore + 0.06 × HousingBurdenScore
```

> 权重定义以 `src/yei/config.py` 中的 `YEOI_WEIGHTS` 为准。

**核心图表**：

- 最新年份 Top 10 YEOI 排名
- 排名随时间变化折线图
- 城市分组平均 YEOI
- Top 城市分项得分对比

**优先级**：在 03 之后完善。

---

### 05 Explanatory Model — 解释与稳健性（非因果）

**目标**：讨论哪些因素与 YEOI 排名关联，并检验权重敏感性。**不做**复杂机器学习或因果推断。

**建议内容**：

- 各分项得分与 `yeoi_score` 的相关性
- 城市分组平均分对比
- Top / Bottom 城市的指标差异
- **权重敏感性分析**：
  - 基准权重
  - 提高住房权重
  - 提高人口增长权重
  - 降低创新权重
- 比较不同权重下排名是否稳定

**核心输出**：

- 分项与 YEOI 相关性条形图
- Top / Bottom 城市分项差异表
- 敏感性排名变化表
- 稳定排名城市 vs 敏感排名城市

**表述原则**：

```text
This is an explanatory index analysis, not a causal model.
```

应写「在当前指数设定下，收入与 GDP 分项对排名贡献较大」，而非「收入导致城市机会更高」。

**优先级**：最后完善，用于补充稳健性与 limitation。

---

## 3. 贯穿全系列的核心问题

| # | 问题 |
|---|------|
| 1 | 哪些城市收入机会最高？ |
| 2 | 哪些城市住房压力最低？ |
| 3 | 哪些城市在人口增长上仍有吸引力？ |
| 4 | 高收入是否一定意味着高经济机会？ |
| 5 | 哪些城市在「收入高 + 住房压力可接受」之间更平衡？ |
| 6 | YEOI 排名前列城市主要靠哪类优势？ |
| 7 | 若提高住房压力权重，排名是否会明显变化？ |
| 8 | 哪些结论受 `rd_expenditure` 缺失影响最大？ |

---

## 4. 当前数据状态对分析的影响

截至项目当前状态（详见 `data/raw/missing_data_summary.md`，本地未入库）：

| 指标 | 面板覆盖 | 对分析的影响 |
|------|----------|--------------|
| `disposable_income` | 100/100 | 可完整做收入排名与散点图 |
| `house_price` / `housing_burden` | 100/100 | 可完整做住房压力分析 |
| `population_growth` | 100/100 | 可完整做增长趋势 |
| `gdp_per_capita` | 100/100 | 可完整做 GDP 对比 |
| `innovation_index` | 91/100 | 成都/合肥 2024 及 7 城 2025 缺失；创新分项与 YEOI 在该年为空 |

在 04、05 中应标注：涉及缺失年份的城市，创新分项与综合排名需审慎解读。

---

## 5. 实施优先级

| 顺序 | Notebook | 理由 |
|------|----------|------|
| 1 | `03_exploratory_analysis.ipynb` | 产出核心图表与经济叙事 |
| 2 | `04_index_calculation.ipynb` | 排名、分项、权重解释 |
| 3 | `05_explanatory_model.ipynb` | 稳健性与 sensitivity |
| 4 | `01_data_sources.ipynb` | 保持简洁，支撑可信度 |
| 5 | `02_data_cleaning.ipynb` | 保持简洁，指向 `src/yei/` |

---

## 6. 与报告、Dashboard 的衔接

| 产出 | 去向 |
|------|------|
| 03 中 5 张核心图 | `reports/` 静态图或报告插图 |
| 04 排名表 | 报告 Results 节 |
| 05 敏感性结论 | 报告 Limitations / Discussion |
| 04 交互需求 | `app/streamlit_app.py` 已实现年份、城市、分项查询 |

Notebook 结论应服务于 [project-design.md](project-design.md) 第 10 节报告结构：Introduction → Data → Methodology → Results → Discussion → Limitations → Conclusion。

---

## 7. 相关文档

- [项目设计](project-design.md)
- [方法论](methodology.md)
- [数据设计](data-design.md)
- [架构与命令](architecture.md)
