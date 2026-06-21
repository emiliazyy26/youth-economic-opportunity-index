# 数据设计

## 目标数据表

最终面板数据保存为 `data/processed/city_economic_opportunity.csv`。

### 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `city` | string | 城市英文名 |
| `year` | int | 年份 |
| `gdp_per_capita` | float | 人均 GDP（元） |
| `disposable_income` | float | 居民人均可支配收入（元） |
| `house_price` | float | 住房价格水平（元/㎡ 或指数换算后的可比价格） |
| `housing_burden` | float | 住房负担，默认 `house_price / disposable_income` |
| `population_growth` | float | 人口同比增长率 |
| `university_resource` | int | 高校数量（辅助解释变量） |
| `innovation_index` | float | 创新能力综合指标 |

### 指数输出表

`data/processed/ueoi_scores.csv` 在原始字段基础上追加：

| 字段 | 说明 |
|------|------|
| `income_score` | 收入得分（0–100） |
| `gdp_score` | 人均 GDP 得分 |
| `population_growth_score` | 人口增长得分 |
| `innovation_score` | 创新得分 |
| `housing_burden_score` | 住房负担得分（负担越低分越高） |
| `ueoi_score` | 综合指数 |
| `rank` | 同一年份内排名 |

## 数据分层与原始数据入口

项目数据分为三层：

```text
data/raw/        # source-backed 原始观测和来源元数据，不写估算或 proxy
data/interim/    # 年度房价指数、人口增长、住房负担等可复现派生表
data/processed/  # 清洗后的分析表和 UEOI 分数
```

source-backed 长表保存为：

```text
data/raw/source_observations.csv
```

缺失项报告保存为：

```text
data/raw/missing_data_report.csv
```

`data/raw/city_panel.csv` 是从 source observations 透视得到的宽表，允许缺失。列名需与上表一致（小写 snake_case）。字段、单位、口径和来源说明集中维护在：

```text
data/data_dictionary.md
```

`data_dictionary.md` 是面向复核的说明文件；真正参与计算的数据仍来自 source-backed raw、interim 派生表和 processed 输出。

## 数据来源

### 1. GDP 与人口 — 国家统计局 / 城市统计年鉴

- GDP、人均 GDP、常住人口
- 可靠性：★★★★★
- 用途：经济规模与人口增长计算

### 2. 居民收入 — 城市统计年鉴

- 城镇居民 / 农村居民人均可支配收入
- 可靠性：★★★★★
- 用途：UEOI 中最重要的正向指标（权重 35%）

### 3. 房价 — 官方指数 + 基准价换算

**核心原则：** 不使用无法向招生官验证的来源（链家截图、贝壳报告、财经文章）。

**推荐方案 A（主方案）：**

- 国家统计局 70 城房价指数
- 覆盖本项目大部分样本城市
- 缺点：指数为相对变化，非绝对价格
- 处理：以某基准年（如 2025）可比价格水平 + 历史指数回推

**推荐方案 B（补充，仅作 Supplementary）：**

- 房租数据（Numbeo 等）
- 不进入核心 UEOI 计算

### 4. 创新能力 — 城市统计年鉴

- R&D 支出、高技术产业等
- 可构建简单创新指数或选取单一官方指标

### 5. 大学资源 — 教育部高校名单

- 指标：城市内高校数量
- 用途：解释年轻人才流入，不直接进入 UEOI 主公式

## 数据质量检查清单

- [ ] 20 个城市全部覆盖
- [ ] 2021–2025 每年均有记录
- [ ] 收入、GDP 单位统一为「元」
- [ ] 房价数据可追溯至官方来源
- [ ] `housing_burden` 计算方式在报告中明确说明
- [ ] 缺失值保留为空，并在 `data/raw/missing_data_report.csv` 中披露；不使用不可复核估算或 proxy 补 raw 数据
- [ ] `data/data_dictionary.md` 已记录字段口径、单位、来源和处理假设

## Notebook 与数据设计关系

`notebooks/` 用于展示数据来源、清洗检查、探索性分析和指数解释。Notebook 可以读取 `data/raw/` 与 `data/processed/`，也可以调用 `src/uei/` 的函数；但清洗、标准化和排名逻辑应以 `src/uei/` 为准，避免 notebook 与生产代码出现两套口径。

## 数据收集优先级

1. **必须：** 可支配收入、人均 GDP、人口、住房负担
2. **重要：** 创新指标、人口增长率
3. **辅助：** 高校数量（用于 Discussion，非指数核心）
