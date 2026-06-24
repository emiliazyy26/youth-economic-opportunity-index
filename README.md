# Urban Economic Opportunity Index (UEOI / YEOI)

中国青年城市机会指数：就业、起薪与生活成本的数据分析研究。

**English:** Urban Economic Opportunity Index for Young Professionals in China — jobs, starting income, living cost and city attractiveness.

## 研究问题

> For young people, which Chinese cities provide the best balance between job opportunity, starting income and living cost?

本项目构建面向**年轻人与职场早期人群**的透明、可解释城市机会指数（YEOI），而非房价预测或机器学习黑箱模型。

## 快速开始

```bash
uv sync
uv run ueoi-download   # 可选：刷新原始数据
uv run ueoi-build      # 构建 YEOI
uv run streamlit run app/streamlit_app.py
```

## 指数公式

```text
YEOI = 0.25 × JobOpportunity + 0.20 × StartingIncome
     + 0.20 × LivingCost + 0.15 × BigCompany
     + 0.10 × GrowthPotential + 0.10 × CityBase
```

招聘、租金等第三方数据通过可信度门槛后可进入主排名；详见 [docs/methodology.md](docs/methodology.md)。

## 核心输出

| 文件 | 说明 |
|------|------|
| `data/processed/city_economic_opportunity.csv` | 城市 × 年份面板 |
| `data/processed/yeoi_scores.csv` | YEOI 分项与排名 |
| `data/processed/sensitivity_report.csv` | 权重敏感性分析 |
| `app/streamlit_app.py` | 交互式 Dashboard |

## 文档

- [项目设计](docs/project-design.md)
- [数据设计](docs/data-design.md)
- [方法论](docs/methodology.md)
- [数据字典](data/data_dictionary.md)

## 技术栈

Python 3.12+ · uv · pandas · streamlit · pytest · ruff

## 许可证

MIT
