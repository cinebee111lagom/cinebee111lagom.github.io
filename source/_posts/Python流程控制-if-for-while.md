---
title: Python 流程控制：if、for、while
date: 2026-08-21 09:45:00
tags:
  - Python
  - 流程控制
categories:
  - Python 新手入门
---

流程控制决定程序的执行顺序，是编程的核心逻辑。

## if 条件分支

```python
score = 85

if score >= 90:
    print("优秀")
elif score >= 60:
    print("及格")
else:
    print("不及格")
```

缩进（4 空格）表示代码块，**不要用 Tab 混用**。

## 三元表达式

```python
result = "通过" if score >= 60 else "不通过"
```

## for 循环

```python
for i in range(5):      # 0,1,2,3,4
    print(i)

for i in range(1, 6):   # 1~5
    print(i)

for i in range(0, 10, 2):  # 0,2,4,6,8
    print(i)

fruits = ["apple", "banana"]
for f in fruits:
    print(f)

for idx, f in enumerate(fruits):
    print(idx, f)
```

## while 循环

```python
count = 0
while count < 5:
    print(count)
    count += 1
```

## break 与 continue

```python
for i in range(10):
    if i == 3:
        continue    # 跳过本次
    if i == 7:
        break       # 退出循环
    print(i)
```

## match（Python 3.10+）

```python
status = 404
match status:
    case 200:
        print("OK")
    case 404:
        print("Not Found")
    case _:
        print("Other")
```

类似 switch，处理多分支更清晰。

## 真值判断

```python
if name:          # 非空字符串为 True
    print(name)
if not items:     # 空列表为 False
    print("empty")
```

假值：`False`、`0`、`""`、`[]`、`{}`、`None`。

掌握 if/for/while 即可写出大部分小脚本逻辑。
