---
title: Python 函数入门
date: 2026-08-21 10:15:00
tags:
  - Python
  - 函数
categories:
  - Python 新手入门
---

函数把代码封装成可复用块，是组织程序的基本单元。

## 定义与调用

```python
def greet(name):
    """向用户打招呼"""
    return f"Hello, {name}!"

msg = greet("旺仔")
print(msg)
```

## 参数类型

```python
# 默认参数
def power(base, exp=2):
    return base ** exp

power(3)       # 9
power(3, 3)    # 27

# 关键字参数
power(exp=3, base=2)

# 可变参数
def total(*args):
    return sum(args)

total(1, 2, 3)  # 6

def show(**kwargs):
    for k, v in kwargs.items():
        print(k, v)

show(name="A", age=20)
```

## 返回值

```python
def min_max(nums):
    return min(nums), max(nums)

lo, hi = min_max([3, 1, 4, 1, 5])
```

## 作用域

```python
x = 10  # 全局

def foo():
    x = 20      # 局部，不影响全局
    print(x)

def bar():
    global x
    x = 30      # 修改全局（慎用）
```

## lambda 匿名函数

```python
square = lambda x: x ** 2
square(5)  # 25

nums = [1, 2, 3, 4]
list(map(lambda x: x * 2, nums))  # [2, 4, 6, 8]
```

## 常用内置函数

```python
len([1, 2, 3])
sorted([3, 1, 2])
max([1, 5, 3])
min([1, 5, 3])
sum([1, 2, 3])
all([True, True])
any([False, True])
```

函数应**单一职责**，名称为动词：`get_user`、`calc_total`。
