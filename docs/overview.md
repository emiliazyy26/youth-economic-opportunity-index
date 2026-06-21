# 项目概述

## 项目名称

**Urban Economic Opportunity Index (UEOI)**  
中国城市经济机会指数

## 英文标题

Measuring Urban Economic Opportunity in China: A Data-Driven Analysis of Income, Housing Affordability and Growth Potential

## 核心研究问题

> For young people, which Chinese cities provide the best balance between economic opportunity and living cost?

年轻人选择城市时面临三个经济学问题：

1. 高收入城市是否值得承受更高的房价？
2. 住房压力是否会抵消经济机会？
3. 哪些城市具有更好的长期吸引力？

## 项目定位

| 要做 | 不要做 |
|------|--------|
| 构建透明、可解释的城市经济机会指数 | 全国房价排名 |
| 多维度比较 20 个样本城市 | 房地产投资建议 |
| 用官方可验证数据支撑结论 | 网页爬虫或非官方二手数据作为核心依据 |
| Python 数据分析 + Streamlit 展示 | 机器学习黑箱预测 |

## 样本范围

- **城市数量：** 20
- **时间跨度：** 5 年（2021–2025）
- **数据规模：** 约 100 行面板数据

### 城市分组

| 类别 | 城市 |
|------|------|
| 超大城市 | Beijing, Shanghai, Shenzhen, Guangzhou |
| 强二线 | Hangzhou, Nanjing, Suzhou, Chengdu, Wuhan, Xi'an |
| 转型城市 | Hefei, Changsha, Qingdao, Xiamen, Zhengzhou, Chongqing |
| 对照组 | Harbin, Shenyang, Kunming, Nanchang |

## 交付物

| 阶段 | 输出 |
|------|------|
| 数据 | `data/processed/city_economic_opportunity.csv` |
| 指数 | `data/processed/ueoi_scores.csv` |
| 分析 | 5 张核心图表（收入、住房负担、GDP、人口变化、UEOI 排名） |
| 产品 | Streamlit Dashboard |
| 报告 | 8 页经济学分析报告 |

## 两周里程碑

| 时间 | 任务 |
|------|------|
| Day 1–3 | 数据收集，完成 raw CSV |
| Day 4–6 | Python 清洗、归一化、相关性分析、出图 |
| Day 7–10 | Streamlit Dashboard |
| Day 11–13 | 经济报告撰写 |
| Day 14 | GitHub 整理与文档完善 |

## 相关文档

- [数据设计](data-design.md)
- [方法论](methodology.md)
- [架构与开发指南](architecture.md)
