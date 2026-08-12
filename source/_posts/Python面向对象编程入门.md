---
title: Python 面向对象编程入门
date: 2026-08-21 11:00:00
tags:
  - Python
  - OOP
categories:
  - Python 新手入门
---

面向对象（OOP）用「类」和「对象」组织代码，适合复杂业务建模。

## 类与对象

```python
class Dog:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def bark(self):
        return f"{self.name}: 汪汪!"

d = Dog("旺财", 3)
print(d.bark())
print(d.name)
```

- `__init__`：构造方法
- `self`：实例自身引用
- 方法第一个参数必须是 `self`

## 属性与方法

```python
class User:
    def __init__(self, name):
        self._name = name      # 约定「私有」

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not value:
            raise ValueError("名字不能为空")
        self._name = value
```

## 继承

```python
class Animal:
    def speak(self):
        return "..."

class Cat(Animal):
    def speak(self):
        return "喵"

class Dog(Animal):
    def speak(self):
        return "汪"

def make_speak(animal: Animal):
    print(animal.speak())   # 多态
```

## 类方法与静态方法

```python
class Counter:
    count = 0

    def __init__(self):
        Counter.count += 1

    @classmethod
    def get_count(cls):
        return cls.count

    @staticmethod
    def add(a, b):
        return a + b
```

## dataclass（简化数据类，3.7+）

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float

p = Point(1.0, 2.0)
print(p)  # Point(x=1.0, y=2.0)
```

## 何时用 OOP

| 用 | 不用 |
|----|------|
| 复杂业务实体 | 10 行脚本 |
| 需要继承扩展 | 纯函数够用 |
| 状态 + 行为封装 | 简单数据处理 |

Python 也支持**过程式 + 函数式**，不必一切皆类。
