---
title: Python 数据结构：列表、元组、字典、集合
date: 2026-08-21 10:00:00
tags:
  - Python
  - 数据结构
categories:
  - Python 新手入门
---

四种内置容器是 Python 最常用的数据结构。

## 列表 list（可变、有序）

```python
nums = [1, 2, 3, 4]
nums.append(5)
nums.insert(0, 0)
nums.pop()           # 删最后一个
nums[0]              # 索引，从 0 开始
nums[-1]             # 最后一个
nums[1:3]            # 切片 [2, 3]
len(nums)
```

## 元组 tuple（不可变、有序）

```python
point = (10, 20)
x, y = point         # 解包
# point[0] = 5      # 报错，不可改
```

用于固定组合，如坐标、函数多返回值。

## 字典 dict（键值对）

```python
user = {"name": "旺仔", "age": 25}
user["name"]         # "旺仔"
user.get("email", "无")  # 默认值
user["city"] = "上海"
user.keys()
user.values()
user.items()

for k, v in user.items():
    print(k, v)
```

## 集合 set（无序、不重复）

```python
s = {1, 2, 3, 2}     # {1, 2, 3}
s.add(4)
s.remove(2)
a = {1, 2, 3}
b = {2, 3, 4}
a & b                # 交集 {2, 3}
a | b                # 并集
```

## 对比

| | 有序 | 可变 | 重复 | 用途 |
|---|------|------|------|------|
| list | ✅ | ✅ | ✅ | 通用序列 |
| tuple | ✅ | ❌ | ✅ | 固定数据 |
| dict | ❌* | ✅ | key 唯一 | 映射 |
| set | ❌ | ✅ | ❌ | 去重、集合运算 |

## 嵌套

```python
users = [
    {"name": "A", "tags": ["admin", "dev"]},
    {"name": "B", "tags": ["ops"]},
]
users[0]["tags"][0]  # "admin"
```

数据结构选对了，代码会简洁很多。
