# 方法论

## 设计原则

UEOI 采用**透明加权线性模型**，而非机器学习。原因：

- 本科经济学申请更看重可解释性
- 权重具有明确经济含义
- 结果可被独立复核

## 指数公式

```text
UEOI = 0.35 × Income
     + 0.25 × GDP
     + 0.15 × PopulationGrowth
     + 0.15 × Innovation
     + 0.10 × HousingAffordability
```

其中各项均为 **0–100 的标准化得分**，在同一年份的城市截面内计算；`HousingAffordability` 是对住房负担反向标准化后的得分，分数越高表示住房压力越低。

## 权重说明

| 指标 | 权重 | 经济含义 |
|------|------|----------|
| Income | +0.35 | 实际购买力与生活质量的核心 proxy |
| GDP per capita | +0.25 | 城市经济基础与就业容量 |
| Population growth | +0.15 | 人口流入反映城市吸引力 |
| Innovation | +0.15 | 长期增长潜力 |
| Housing affordability | +0.10 | 由住房负担反向标准化得到；分数越高代表生活成本压力越低，权重绝对值较小，避免「低房价=高机会」的简化结论 |

## 标准化方法

### Min-Max 归一化

对正向指标（收入、GDP、人口增长、创新）：

```text
Score_i = (x_i - min(x)) / (max(x) - min(x)) × 100
```

对住房负担（越低越好）：

```text
Score_i = (max(x) - x_i) / (max(x) - min(x)) × 100
```

**注意：** 归一化在**每个年份截面**内独立进行，保证跨城比较在同一年份内公平。

### 边界情况

当某年所有城市某指标取值相同（`max = min`）时，该项得分统一设为 50，避免除零。

## 派生指标

### 住房负担

```text
HousingBurden = HousePrice / DisposableIncome
```

该比值衡量「购买力的住房压力」，比单独使用房价更符合经济学框架。

### 人口增长

```text
PopulationGrowth_t = (Population_t - Population_{t-1}) / Population_{t-1}
```

## 排名规则

- 按 `ueoi_score` 降序排名
- 同分城市取相同名次（`method='min'`）
- 排名仅在同一 `{year}` 截面内有效

## 敏感性分析（可选扩展）

可在报告中讨论：

1. 调整住房可负担性权重（+0.05 / +0.15）对排名的影响
2. 去掉创新指标后 Top 5 城市是否稳定
3. 收入与住房负担的相关性是否削弱高收入城市的优势

## 实现入口

代码位于 `src/uei/build_index.py`：

```bash
uv run ueoi-build
```

配置常量（城市列表、权重）位于 `src/uei/config.py`。
