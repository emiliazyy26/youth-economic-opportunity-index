# Urban Economic Opportunity Index 项目设计

## 1. 项目定位

**Urban Economic Opportunity Index (UEOI / YEOI)** 是一个面向中国城市比较、**聚焦年轻人与职场早期人群**的经济数据分析项目。项目关注毕业生和青年职场人在选择城市时的核心权衡：就业机会、起薪回报、生活成本、大企业机会与长期增长潜力。

中文标题：

```text
中国青年城市机会指数：就业、起薪与生活成本的数据分析研究
```

英文标题：

```text
Urban Economic Opportunity Index for Young Professionals in China:
A Data-Driven Analysis of Jobs, Starting Income and Living Cost
```

项目不做简单的房价排名，也不做房地产投资判断。研究重点是：**哪些中国城市为年轻人提供了更好的就业机会与生活成本平衡**。

## 2. 研究问题

核心问题：

```text
For young people, which Chinese cities provide the best balance
between economic opportunity and living cost?
```

具体拆解为三个经济学问题：

1. 高收入城市是否仍然值得承受更高住房成本？
2. 住房压力是否会抵消城市提供的经济机会？
3. 哪些城市具有更好的长期吸引力和增长潜力？

本项目的分析对象是城市经济机会，而不是住房市场本身。房价和住房压力只作为生活成本约束进入指数。

## 3. 项目边界

### 要做

| 方向 | 说明 |
|------|------|
| 城市青年机会比较 | 比较岗位机会、起薪、生活成本、大企业数量、增长潜力 |
| 透明指数构建 | 使用可解释的线性加权模型（YEOI） |
| 可信数据优先 | 官方统计 + 可复核机构数据 + 通过质量门槛的平台样本 |
| Python 数据分析 | 使用 pandas、numpy、plotly、matplotlib 完成分析与可视化 |
| Streamlit Dashboard | 提供交互式城市查询和排名展示 |

### 不做

| 不做 | 原因 |
|------|------|
| 中国房价排行榜 | 容易变成房地产项目，偏离经济学主题 |
| 房地产投资建议 | 与项目目标和申请展示不匹配 |
| 机器学习预测 | 当前数据规模小，透明模型更合适 |
| 大规模网页爬虫 | 数据可验证性弱，维护成本高 |

## 4. 样本设计

### 时间范围

分析时间段为 **2021–2025**。

需要额外收集 **2020 年常住人口**，用于计算 2021 年人口增长率：

```text
PopulationGrowth_2021 = (Population_2021 - Population_2020) / Population_2020
```

因此数据下载建议为：

| 目的 | 下载范围 |
|------|----------|
| 核心分析 | 2022–2026 年版《中国城市统计年鉴》，对应 2021–2025 数据 |
| 人口增长计算 | 额外下载 2021 年版年鉴，用于补充 2020 人口 |

最终分析表仍保持 **20 个城市 × 5 年 = 100 行**。

### 城市范围

项目选择 20 个城市，避免全国铺开，形成有解释力的分组比较。

| 城市类型 | 城市 |
|----------|------|
| 超大城市 | Beijing, Shanghai, Shenzhen, Guangzhou |
| 强二线城市 | Hangzhou, Nanjing, Suzhou, Chengdu, Wuhan, Xi'an |
| 转型与成长城市 | Hefei, Changsha, Qingdao, Xiamen, Zhengzhou, Chongqing |
| 对照组城市 | Harbin, Shenyang, Kunming, Nanchang |

城市选择逻辑：

1. 覆盖一线、强二线、成长型和转型城市；
2. 兼顾东部、内陆、东北和西南地区；
3. 多数城市能在官方统计资料中找到连续数据；
4. 样本规模适合短周期完成收集、清洗、分析和展示。

## 5. 数据设计

### 原始主表

原始数据主表保存为：

```text
data/raw/city_panel.csv
```

建议字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| `city` | string | 城市英文名 |
| `year` | int | 数据年份 |
| `gdp_per_capita` | float | 人均 GDP |
| `disposable_income` | float | 居民人均可支配收入 |
| `house_price` | float | 房价水平或由官方指数换算的可比价格 |
| `housing_burden` | float | 住房负担 |
| `population` | float | 常住人口，用于计算人口增长 |
| `population_growth` | float | 常住人口增长率 |
| `university_quality` | float | 大学质量加权得分 |
| `tertiary_ratio` | float | 第三产业占 GDP 比重（%） |
| `innovation_index` | float | 创新能力指标（R&D 经费） |
| `source` | string | 数据来源简记 |
| `source_url` | string | 原始链接 |
| `notes` | string | 单位、口径或处理说明 |

项目代码中的核心计算字段为：

```text
city
year
gdp_per_capita
disposable_income
house_price
housing_burden
population_growth
university_quality
tertiary_ratio
innovation_index
```

`population`、`source`、`source_url` 和 `notes` 可作为收集过程中的辅助字段保留。

### 输出表

清洗后的面板数据：

```text
data/processed/city_economic_opportunity.csv
```

指数得分表：

```text
data/processed/yeoi_scores.csv
```

指数表包含：

| 字段 | 说明 |
|------|------|
| `job_opportunity_score` | 就业机会标准化得分 |
| `starting_income_score` | 起薪/收入标准化得分 |
| `living_cost_score` | 生活成本可负担性得分（越高压力越低） |
| `big_company_score` | 大企业/上市公司机会得分 |
| `growth_potential_score` | 增长潜力得分 |
| `city_base_score` | 人才资本与城市基础得分 |
| `yeoi_score` | 综合青年城市机会指数 |
| `rank` | 同一年份城市排名 |
| `*_source` | 各维度实际使用的指标来源标签 |

## 6. 数据来源方案

### GDP、人均 GDP 与人口

优先来源：

1. 国家统计局；
2. 《中国城市统计年鉴》；
3. 各城市统计局发布的统计年鉴；
4. 各城市国民经济和社会发展统计公报。

用途：

- `gdp_per_capita` 衡量城市经济基础；
- `population` 用于计算 `population_growth`；
- 人口增长代表城市吸引力和就业机会的综合结果。

### 居民收入

核心指标：

```text
disposable_income = 居民人均可支配收入
```

优先使用全体居民人均可支配收入。如果只有城镇居民收入和农村居民收入，必须保持所有城市口径一致，并在 `notes` 中说明。

收入是 UEOI 中权重最高的指标，因为它直接反映年轻人在城市中的收入机会和实际购买力。

### 房价与住房负担

住房数据必须谨慎处理。项目不应依赖链家截图、贝壳报告、财经文章或无法复核的网络均价。

推荐主方案：

```text
国家统计局 70 个大中城市商品住宅销售价格指数
```

该数据的优点是官方、连续、可验证；缺点是它是指数，不是绝对价格。处理方式可以是：

```text
HousePrice_t = BasePrice_2025 × HousingIndex_t / HousingIndex_2025
```

如果短期内无法获得可靠的绝对基准价，可以先使用官方房价指数构建相对住房压力，并在报告中明确说明：

```text
HousingBurden = HousingIndex / DisposableIncome
```

更理想的定义为：

```text
HousingBurden = HousePrice / DisposableIncome
```

项目解释重点应放在住房压力对经济机会的约束，而不是房价本身。

### 创新能力

创新指标不需要复杂化。优先选择一个官方、连续、易解释的变量：

1. R&D 经费支出；
2. R&D 经费占 GDP 比重；
3. 高技术产业增加值；
4. 专利授权量。

如果多个城市缺失同一指标，应优先降低复杂度，选择覆盖最完整的变量，而不是构造不可复核的复杂综合指数。

### 大学资源

大学资源作为人才资本维度进入 UEOI 主公式（权重 0.15）。

推荐来源：

```text
教育部全国高等学校名单 + 985/211/双一流官方列表
```

指标定义：

```text
university_quality = 985数量 × 5.0 + 211(非985)数量 × 2.5 + 其他普通高校 × 0.3
```

该加权方案区分了大学层级：顶尖研究型大学（985）的权重是普通高校的约 17 倍，准确反映了高端人力资本供给的差异。例如北京（8 所 985）得分远超深圳（0 所 985），而旧方案仅用简单计数无法体现这一差距。

高校数量和层级在 2021–2025 的短期内变化不大，使用 2025 年名单作为近似，并在报告中说明该假设。

## 7. 指数方法

### 设计原则

UEOI 使用透明的线性加权模型，不使用机器学习。

理由：

1. 数据量约 100 行，不适合复杂预测模型；
2. 经济学项目更重视变量定义、机制解释和稳健性；
3. 透明模型便于读者复核；
4. Dashboard 可以直接展示各项得分和最终排名。

### 归一化方法

所有指标在同一年份内按城市截面做 Min-Max 标准化。

正向指标：

```text
Score_i = (x_i - min(x)) / (max(x) - min(x)) × 100
```

住房负担为负向指标，负担越低越好：

```text
HousingBurdenScore_i = (max(x) - x_i) / (max(x) - min(x)) × 100
```

如果某一年某个指标所有城市数值相同，则该项统一设为 50，避免除零。

### 指数公式

```text
YEOI = 0.25 × JobOpportunity
     + 0.20 × StartingIncome
     + 0.20 × LivingCostAffordability
     + 0.15 × BigCompanyOpportunity
     + 0.10 × GrowthPotential
     + 0.10 × HumanCapitalCityBase
```

### 权重解释

| 维度 | 权重 | 解释 |
|------|------|------|
| 就业机会 | 0.25 | 岗位数量或就业容量，直接反映青年能否找到工作 |
| 起薪/收入 | 0.20 | 起薪优先，不足时用可支配收入 |
| 生活成本 | 0.20 | 租金负担优先，不足时用住房负担 |
| 大企业机会 | 0.15 | 上市公司/大企业数量 |
| 增长潜力 | 0.10 | 人口增长 + 创新活动 |
| 城市基础 | 0.10 | 大学质量 + 人均 GDP（降权避免宏观排名） |

第三方数据（招聘、租金）通过可信度门槛后可进入主指数；未达标则自动 fallback。

## 8. 分析输出

### 核心图表

至少完成 5 张图：

1. 收入排名；
2. 住房负担排名；
3. 人均 GDP 对比；
4. 人口增长变化；
5. UEOI 最终排名。

可选扩展图：

1. 收入 vs 住房负担散点图；
2. UEOI 排名变化折线图；
3. 城市分组箱线图；
4. 指标相关性热力图。

### Dashboard 输出

Streamlit Dashboard 应支持：

1. 选择年份；
2. 选择城市；
3. 查看城市 UEOI 总分；
4. 查看城市排名；
5. 查看收入、GDP、人口增长、创新、住房负担的分项得分；
6. 查看同一年份所有城市排名表。

城市页面示例：

| 指标 | 输出 |
|------|------|
| UEOI Score | 82.0 |
| Rank | No.3 / 20 |
| Income Score | 95 |
| GDP Score | 92 |
| Housing Burden Score | 45 |

## 9. 技术实现

### 技术栈

| 工具 | 用途 |
|------|------|
| Python 3.12 | 主语言 |
| uv | 依赖与虚拟环境管理 |
| pandas | 数据清洗和面板表处理 |
| numpy | 数值计算 |
| matplotlib | 报告静态图 |
| plotly | 交互式图表 |
| streamlit | Dashboard |
| pytest | 单元测试 |
| ruff | 代码检查 |

### 项目结构

```text
urban-economic-opportunity-index/
├── app/
│   └── streamlit_app.py
├── data/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── project-design.md
│   ├── overview.md
│   ├── data-design.md
│   ├── methodology.md
│   └── architecture.md
├── notebooks/
├── src/
│   └── uei/
│       ├── config.py
│       ├── clean_data.py
│       ├── build_index.py
│       └── visualize.py
└── tests/
```

### 数据流水线

```text
data/raw/city_panel.csv
        │
        ▼
src/uei/clean_data.py
        │
        ▼
data/processed/city_economic_opportunity.csv
        │
        ▼
src/uei/build_index.py
        │
        ▼
data/processed/yeoi_scores.csv
        │
        ├── data/processed/sensitivity_report.csv
        ├── reports / figures
        └── Streamlit Dashboard
```

### 常用命令

```bash
uv sync
uv run ueoi-build
uv run pytest
uv run ruff check src tests
uv run streamlit run app/streamlit_app.py
```

## 10. 报告结构

最终报告建议控制在 8 页左右。

| 部分 | 内容 |
|------|------|
| Introduction | 研究问题、城市选择背景 |
| Literature / Context | 城市机会、收入、住房负担、人口流动 |
| Data | 数据来源、变量定义、样本范围 |
| Methodology | 标准化、权重、YEOI 公式与 fallback |
| Results | 排名、图表、城市分组比较 |
| Discussion | 高收入高成本城市与成长型城市的权衡 |
| Limitations | 房价指数、数据缺失、权重主观性 |
| Conclusion | 哪些城市更平衡，以及对年轻人的意义 |

## 11. 执行计划

| 时间 | 任务 | 输出 |
|------|------|------|
| Day 1–3 | 下载统计年鉴与房价指数，整理 `city_panel.csv` | 原始数据表 |
| Day 4 | 清洗数据，统一单位，处理缺失值 | `city_economic_opportunity.csv` |
| Day 5 | 构建 YEOI 标准化得分 | `yeoi_scores.csv` |
| Day 6 | 生成核心图表与敏感性分析 | figures + sensitivity_report |
| Day 7–9 | 开发 Streamlit Dashboard | 可交互页面 |
| Day 10 | 增加城市对比、排名表和分项展示 | Dashboard 完成版 |
| Day 11–12 | 撰写经济报告 | 报告初稿 |
| Day 13 | 检查数据来源、补充 limitation 和 sensitivity | 报告定稿 |
| Day 14 | GitHub 整理、README 和最终检查 | 完整作品集 |

## 12. 风险与处理

| 风险 | 处理方式 |
|------|----------|
| 某些城市缺少完整收入数据 | 优先用统计公报补充；仍缺失则记录并考虑删除该城市 |
| 房价绝对水平不可验证 | 使用官方 70 城指数构造相对住房压力 |
| 创新指标口径不一致 | 选择覆盖率最高的单一指标 |
| 权重具有主观性 | 在报告中加入敏感性分析 |
| 数据收集耗时过长 | 先完成 20 城核心 5 指标，再补充高校和创新 |

## 13. 成功标准

项目完成时应达到：

1. `data/raw/city_panel.csv` 覆盖 20 城 × 2021–2025；
2. 每条核心数据都有来源记录；
3. 能通过 `uv run ueoi-build` 生成指数结果；
4. 至少有 5 张可用于报告的图表；
5. Streamlit Dashboard 可选择城市和年份；
6. 报告能清楚解释为什么项目是“青年城市机会指数”，不是“房价研究”。

## 14. 项目价值

该项目适合作为经济学与数据分析方向的申请作品集，因为它同时展示：

1. 经济学问题意识；
2. 官方数据收集与清洗能力；
3. 指数构建和量化比较能力；
4. Python 数据分析能力；
5. Dashboard 产品化表达能力；
6. 对模型局限性和数据口径的认识。

最终叙事应保持简单：

```text
This project measures urban economic opportunity in China by combining
income, economic scale, population attraction, innovation potential and
housing burden into a transparent, reproducible index.
```
