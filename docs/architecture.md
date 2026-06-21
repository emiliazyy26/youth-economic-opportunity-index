# 架构与开发指南

## 目录结构

```text
urban-economic-opportunity-index/
├── app/
│   └── streamlit_app.py       # Dashboard 入口
├── data/
│   ├── raw/                   # 手工收集的原始 CSV
│   ├── processed/             # 清洗结果与指数输出
│   └── data_dictionary.md     # 字段、单位、口径与来源说明
├── docs/                      # 项目文档
├── notebooks/                 # Jupyter 研究过程展示
│   ├── 01_data_sources.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_exploratory_analysis.ipynb
│   ├── 04_index_calculation.ipynb
│   └── 05_explanatory_model.ipynb
├── reports/                   # 申请展示用研究报告输出
├── src/
│   └── uei/                   # 核心 Python 包
│       ├── config.py          # 路径、城市、权重常量
│       ├── clean_data.py      # 清洗与字段派生
│       ├── build_index.py     # UEOI 计算流水线
│       └── visualize.py       # 静态图表
├── tests/
├── pyproject.toml
└── README.md
```

## 数据流

```text
data/raw/city_panel.csv
        │
        ▼  clean_data.py
data/processed/city_economic_opportunity.csv
        │
        ▼  build_index.py
data/processed/ueoi_scores.csv
        │
        ├──► visualize.py  →  figures/
        └──► streamlit_app.py
```

`src/uei/` 是正式、可复现的数据生产链路；`notebooks/` 用来展示研究过程、探索分析和经济学解释。Notebook 可以调用 `src/uei/` 中的函数，但不应复制一套独立的清洗和指数计算逻辑。

## Notebook 设计

| Notebook | 作用 |
|------|------|
| `01_data_sources.ipynb` | 说明样本城市、数据来源、字段口径和来源可验证性 |
| `02_data_cleaning.ipynb` | 展示缺失值检查、单位统一、字段命名和住房负担派生 |
| `03_exploratory_analysis.ipynb` | 分析收入、GDP、住房压力、人口增长和创新指标关系 |
| `04_index_calculation.ipynb` | 解释标准化、权重、UEOI 排名和敏感性分析 |
| `05_explanatory_model.ipynb` | 可选的解释性回归或相关性分析，不作为预测模型主线 |
 
Notebook 的定位是 research narrative，面向招生官展示分析思路；命令行入口 `uv run ueoi-build` 仍然是项目的权威计算入口。

## 环境管理

本项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 版本与依赖。

```bash
# 安装依赖
uv sync

# 安装含开发依赖
uv sync --group dev
```

虚拟环境位于 `.venv/`，无需手动激活即可通过 `uv run` 执行命令。

## 常用命令

```bash
# 构建指数
uv run ueoi-build

# 运行测试
uv run pytest

# 代码检查
uv run ruff check src tests

# 启动 Dashboard
uv run streamlit run app/streamlit_app.py
```

## 模块职责

| 模块 | 职责 |
|------|------|
| `config.py` | 集中管理路径、样本城市、UEOI 权重 |
| `clean_data.py` | 读取 raw 数据、派生 housing_burden、写出 processed 表 |
| `build_index.py` | Min-Max 归一化、加权求和、排名 |
| `visualize.py` | matplotlib 静态图，供报告使用 |
| `app/streamlit_app.py` | 交互式城市查询与排名展示 |
| `notebooks/` | 研究过程展示和探索性分析 |

## 开发约定

1. **列名统一** 使用小写 snake_case
2. **配置集中** 城市列表与权重只改 `config.py`
3. **raw 与 processed 分离** 原始数据不做就地修改
4. **按年截面归一化** 不跨年份混合 min/max
5. **notebooks 不复制生产逻辑** 需要复用清洗或指数计算时从 `src/uei/` 导入
6. **先数据后产品** Day 1–6 完成 CSV、notebook 和图表后再做 Dashboard

## 下一步开发任务

- [ ] 完成 `data/raw/city_panel.csv` 数据收集
- [ ] 完成 `data/data_dictionary.md` 字段、口径和来源说明
- [ ] 补充 5 个研究展示 notebook
- [ ] 补充 5 张核心分析图（收入、住房负担、GDP、人口、UEOI）
- [ ] 完善 Dashboard 多城市对比视图
- [ ] 撰写 8 页经济学报告

## 扩展点

| 需求 | 建议位置 |
|------|----------|
| 新增数据源 | `data/raw/` + `clean_data.py` |
| 调整权重 | `config.py` → `UEOI_WEIGHTS` |
| 新增图表 | `visualize.py` |
| 敏感性分析 | `notebooks/` 或新增 `src/uei/sensitivity.py` |
| 申请报告图表 | `visualize.py` → `reports/` |
