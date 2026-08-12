---
title: Python 列表推导式与生成器
date: 2026-08-21 11:45:00
tags:
  - Python
  - 推导式
  - 生成器
categories:
  - Python 新手入门
---

推导式和生成器是 Python 的「语法糖」，让代码更简洁高效。

## 列表推导式

```python
# 传统
squares = []
for x in range(10):
    squares.append(x ** 2)

# 推导式
squares = [x ** 2 for x in range(10)]
evens = [x for x in range(20) if x % 2 == 0]
matrix = [[i * j for j in range(3)] for i in range(3)]
```

## 字典与集合推导式

```python
{x: x ** 2 for x in range(5)}
# {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

{word for word in ["a", "bb", "ccc"] if len(word) > 1}
# {'bb', 'ccc'}
```

## 生成器表达式

```python
gen = (x ** 2 for x in range(1000000))  # 不占大内存
next(gen)   # 0
next(gen)   # 1

sum(x for x in range(100))  # 直接消费
```

## 生成器函数

```python
def countdown(n):
    while n > 0:
        yield n
        n -= 1

for i in countdown(5):
    print(i)  # 5 4 3 2 1
```

`yield` 暂停函数，下次 `next()` 继续。

## map / filter / zip

```python
list(map(str, [1, 2, 3]))        # ['1', '2', '3']
list(filter(lambda x: x > 0, [-1, 0, 1]))  # [1]
list(zip([1, 2], ["a", "b"]))    # [(1, 'a'), (2, 'b')]
```

推导式通常比 map/filter 更易读。

## 何时用生成器

| 场景 | 选择 |
|------|------|
| 大数据流、逐条处理 | 生成器 |
| 需要多次遍历、索引 | 列表 |
| 一次性转换小数据 | 列表推导式 |

**不要过度嵌套推导式**，超过两层考虑改 for 循环。
