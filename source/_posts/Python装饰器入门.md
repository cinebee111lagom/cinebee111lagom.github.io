---
title: Python 装饰器入门
date: 2026-08-21 12:00:00
tags:
  - Python
  - 装饰器
categories:
  - Python 新手入门
---

装饰器在不改原函数代码的情况下，为其添加额外功能。

## 函数是一等公民

```python
def hello():
    return "hello"

f = hello
f()   # "hello"
```

## 简单装饰器

```python
def log_decorator(func):
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}")
        result = func(*args, **kwargs)
        print(f"返回 {result}")
        return result
    return wrapper

@log_decorator
def add(a, b):
    return a + b

add(1, 2)
# 调用 add
# 返回 3
```

`@log_decorator` 等价于 `add = log_decorator(add)`。

## 带参数的装饰器

```python
def repeat(n):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(n):
                func(*args, **kwargs)
        return wrapper
    return decorator

@repeat(3)
def say_hi():
    print("Hi!")
```

## functools.wraps

```python
from functools import wraps

def log_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

保留原函数名和文档字符串。

## 常见用途

| 用途 | 示例 |
|------|------|
| 日志 | 记录调用 |
| 计时 | 性能统计 |
| 权限 | Web 框架 `@login_required` |
| 缓存 | `@lru_cache` |
| 重试 | 失败自动 retry |

## 内置装饰器

```python
@property
@classmethod
@staticmethod

from functools import lru_cache

@lru_cache(maxsize=128)
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
```

装饰器初看抽象，理解「函数接收函数返回函数」即可。
