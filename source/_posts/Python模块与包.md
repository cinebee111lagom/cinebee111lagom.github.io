---
title: Python 模块与包
date: 2026-08-21 10:30:00
tags:
  - Python
  - 模块
categories:
  - Python 新手入门
---

模块是 `.py` 文件，包是含 `__init__.py` 的目录，用于组织大型项目。

## 导入模块

```python
import math
math.sqrt(16)   # 4.0

from math import sqrt, pi
sqrt(16)

import json as js
js.dumps({"a": 1})

from collections import defaultdict
# 避免 from math import *（污染命名空间）
```

## 自定义模块

```
project/
  main.py
  utils.py
```

```python
# utils.py
def add(a, b):
    return a + b

# main.py
from utils import add
print(add(1, 2))
```

## 包结构

```
mypkg/
  __init__.py
  core.py
  helpers/
    __init__.py
    fmt.py
```

```python
from mypkg.core import foo
from mypkg.helpers.fmt import format_date
```

## `if __name__ == "__main__"`

```python
# utils.py
def helper():
    return "ok"

if __name__ == "__main__":
    # 仅直接运行此文件时执行
    print(helper())
```

被 import 时不执行测试代码。

## 模块搜索路径

```python
import sys
print(sys.path)
```

Python 按当前目录 → PYTHONPATH → 标准库 → site-packages 顺序查找。

## 常用标准库预览

| 模块 | 用途 |
|------|------|
| `os` | 文件、环境变量 |
| `sys` | 解释器、参数 |
| `json` | JSON 解析 |
| `datetime` | 日期时间 |
| `pathlib` | 现代路径操作 |
| `re` | 正则 |

模块化让代码**可维护、可复用**。
