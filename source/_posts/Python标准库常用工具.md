---
title: Python 标准库常用工具
date: 2026-08-21 11:15:00
tags:
  - Python
  - 标准库
categories:
  - Python 新手入门
---

标准库无需安装即可使用，覆盖日常大部分需求。

## datetime 日期时间

```python
from datetime import datetime, timedelta

now = datetime.now()
now.strftime("%Y-%m-%d %H:%M:%S")
datetime.strptime("2026-08-21", "%Y-%m-%d")
now + timedelta(days=7)
```

## json

```python
import json

data = {"name": "旺仔", "age": 25}
s = json.dumps(data, ensure_ascii=False)
obj = json.loads(s)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

## os 与 sys

```python
import os
os.getenv("HOME")
os.listdir(".")
os.path.join("dir", "file.txt")

import sys
sys.argv          # 命令行参数
sys.exit(1)       # 退出码
```

## pathlib

```python
from pathlib import Path

p = Path("logs/app.log")
p.parent.mkdir(parents=True, exist_ok=True)
p.touch()
for f in Path(".").rglob("*.py"):
    print(f)
```

## collections

```python
from collections import Counter, defaultdict, deque

Counter("aabbc")           # {'a': 2, 'b': 2, 'c': 1}
defaultdict(list)          # 默认值工厂
dq = deque([1, 2, 3])
dq.appendleft(0)
```

## random

```python
import random
random.randint(1, 100)
random.choice(["a", "b", "c"])
random.shuffle(items)
```

## argparse 命令行

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("name", help="用户名")
parser.add_argument("-v", "--verbose", action="store_true")
args = parser.parse_args()
print(args.name, args.verbose)
```

```bash
python script.py 旺仔 -v
```

标准库「电池 Included」，写脚本前先查是否有内置模块可用。
