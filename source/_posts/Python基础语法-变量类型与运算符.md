---
title: Python 基础语法：变量、类型与运算符
date: 2026-08-21 09:30:00
tags:
  - Python
  - 语法
categories:
  - Python 新手入门
---

Python 是动态类型语言，变量无需声明类型，但应理解常见数据类型。

## 变量

```python
name = "旺仔"
age = 25
price = 59.9
is_active = True
```

命名规则：字母/下划线开头，区分大小写，推荐 `snake_case`。

## 基本类型

| 类型 | 示例 | 说明 |
|------|------|------|
| `int` | `42` | 整数 |
| `float` | `3.14` | 浮点 |
| `str` | `"hello"` | 字符串 |
| `bool` | `True` / `False` | 布尔 |
| `None` | `None` | 空值 |

```python
type(42)        # <class 'int'>
type("hello")   # <class 'str'>
```

## 类型转换

```python
int("123")      # 123
float("3.14")   # 3.14
str(100)        # "100"
bool(0)         # False
bool("hi")      # True
```

## 字符串

```python
s = "Hello"
s.upper()           # "HELLO"
s + " World"        # 拼接
f"name={name}"      # f-string（推荐）
"{} is {}".format(name, age)
"abc,def".split(",")  # ['abc', 'def']
```

## 运算符

```python
# 算术
10 + 3    # 13
10 // 3   # 3 整除
10 % 3    # 1 取余
2 ** 10   # 1024 幂

# 比较
a == b    # 等于
a != b    # 不等于
a >= b

# 逻辑
a and b
a or b
not a
```

## 输入输出

```python
name = input("请输入姓名: ")
print("你好,", name)
print(f"年龄: {age}", sep=" | ", end="\n")
```

## 注释

```python
# 单行注释

"""
多行文档字符串
常用于函数说明
"""
```

下一篇讲 if、for、while 流程控制。
