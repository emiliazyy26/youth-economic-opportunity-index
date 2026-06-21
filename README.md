# Urban Economic Opportunity Index (UEOI)

中国城市经济机会指数：收入、住房压力与城市吸引力的数据分析研究。

**English:** Measuring Urban Economic Opportunity in China — a data-driven analysis of income, housing affordability, and growth potential.

## 研究问题

> For young people, which Chinese cities provide the best balance between economic opportunity and living cost?

本项目构建一个**透明、可解释**的城市经济机会指数，而非房价预测或机器学习黑箱模型。

## Motivation

Young people often face a trade-off between high-income urban opportunities and rising housing pressure. This project studies that trade-off with official city-level data and presents the results as a reproducible analysis pipeline, research notebooks, and an interactive dashboard.

## 快速开始

```bash
# 安装依赖（需已安装 uv）
uv sync

# 构建指数（需先准备 data/raw/ 下的原始数据）
uv run ueoi-download

# 构建指数
uv run ueoi-build

# 启动 Dashboard
uv run streamlit run app/streamlit_app.py
```

## 项目结构

```
urban-economic-opportunity-index/
├── app/                    # Streamlit Dashboard
├── data/
│   ├── raw/                # 原始数据（统计局、年鉴等）
│   ├── processed/          # 清洗与指数结果 CSV
│   └── data_dictionary.md  # 字段、口径与来源说明
├── docs/                   # 项目文档
├── notebooks/              # 研究过程展示，不作为生产流水线
├── reports/                # 申请展示用研究报告输出
├── src/uei/                # 可复现核心 Python 包
└── tests/                  # 核心计算测试
```

## 核心输出

| 文件 | 说明 |
|------|------|
| `notebooks/01_data_sources.ipynb` | 数据来源、样本城市与字段口径 |
| `notebooks/03_exploratory_analysis.ipynb` | 收入、住房压力、增长和创新的探索分析 |
| `data/processed/city_economic_opportunity.csv` | 最终城市 × 年份数据表 |
| `data/processed/ueoi_scores.csv` | 归一化分项与 UEOI 排名 |
| `app/streamlit_app.py` | 交互式城市经济机会 Dashboard |

## 指数公式

```text
UEOI = 0.35 × Income + 0.25 × GDP + 0.15 × PopulationGrowth
     + 0.15 × Innovation - 0.10 × HousingBurden
```

详见 [docs/methodology.md](docs/methodology.md)。

## 文档

- [项目设计](docs/project-design.md)
- [项目概述](docs/overview.md)
- [数据设计](docs/data-design.md)
- [数据字典](data/data_dictionary.md)
- [方法论](docs/methodology.md)
- [架构与开发指南](docs/architecture.md)

## 技术栈

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — 依赖与虚拟环境管理
- pandas / numpy — 数据处理
- matplotlib / plotly — 可视化
- streamlit — 交互式 Dashboard

## 许可证

MIT
