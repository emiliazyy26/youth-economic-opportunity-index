# 项目概述

## 项目名称

**Youth Economic Opportunity Index (YEOI)**  
中国青年城市机会指数（项目简称仍可用 UEOI）

## 英文标题

Urban Economic Opportunity Index for Young Professionals in China

## 核心研究问题

> For young people, which Chinese cities provide the best balance between job opportunity, starting income and living cost?

## 项目定位

| 要做 | 不要做 |
|------|--------|
| 构建面向年轻人的透明城市机会指数 | 全国房价排名 |
| 比较就业、起薪、生活成本、大企业机会 | 房地产投资建议 |
| 官方 + 可信第三方数据（通过质量门槛） | 不可复现的媒体截图数据 |
| Python 数据分析 + Streamlit 展示 | 机器学习黑箱预测 |

## 样本范围

- **城市数量：** 20
- **时间跨度：** 2021–2025
- **数据规模：** 100 行面板数据

## 交付物

| 阶段 | 输出 |
|------|------|
| 数据 | `data/processed/city_economic_opportunity.csv` |
| 指数 | `data/processed/yeoi_scores.csv` |
| 分析 | 青年视角排名与敏感性报告 |
| 产品 | Streamlit Dashboard |

## 相关文档

- [数据设计](data-design.md)
- [方法论](methodology.md)
- [架构与开发指南](architecture.md)
