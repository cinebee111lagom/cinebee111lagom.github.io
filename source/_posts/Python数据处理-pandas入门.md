---
title: Python 数据处理：pandas 入门
date: 2026-08-21 12:45:00
tags:
  - Python
  - pandas
  - 数据分析
categories:
  - Python 新手入门
---

pandas 是 Python 数据分析核心库，提供类似 Excel 的表格操作。

## 安装与基础

```bash
pip install pandas
```

```python
import pandas as pd

# 从字典创建
df = pd.DataFrame({
    "name": ["A", "B", "C"],
    "age": [25, 30, 28],
    "city": ["上海", "北京", "上海"],
})

# 从 CSV
df = pd.read_csv("data.csv", encoding="utf-8")
df.to_csv("out.csv", index=False)
```

## 查看数据

```python
df.head()       # 前 5 行
df.info()       # 列类型、非空数
df.describe()   # 数值统计
df.shape        # (行, 列)
df.columns
```

## 选择与过滤

```python
df["name"]                    # 单列 Series
df[["name", "age"]]           # 多列
df[df["age"] > 26]            # 条件过滤
df.loc[0, "name"]             # 按标签
df.iloc[0, 1]                 # 按位置
```

## 聚合

```python
df["age"].mean()
df.groupby("city")["age"].mean()
df.groupby("city").agg({"age": "mean", "name": "count"})
```

## 缺失值

```python
df.isnull().sum()
df.dropna()
df.fillna(0)
df["age"].fillna(df["age"].mean())
```

## 合并

```python
pd.merge(df1, df2, on="id", how="left")
pd.concat([df1, df2], axis=0)   # 纵向
```

## 新列

```python
df["age_double"] = df["age"] * 2
df.assign(adult=df["age"] >= 18)
```

pandas 适合 CSV/Excel 清洗、统计、导出，是数据岗位入门必学。
