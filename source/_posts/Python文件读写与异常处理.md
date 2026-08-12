---
title: Python 文件读写与异常处理
date: 2026-08-21 10:45:00
tags:
  - Python
  - 文件
  - 异常
categories:
  - Python 新手入门
---

文件 I/O 和异常处理是写实用脚本的必备技能。

## 读文件

```python
# 推荐 with 自动关闭
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()

with open("data.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line.strip())

lines = open("data.txt", encoding="utf-8").readlines()
```

## 写文件

```python
with open("out.txt", "w", encoding="utf-8") as f:
    f.write("第一行\n")
    f.writelines(["a\n", "b\n"])

# 追加
with open("log.txt", "a", encoding="utf-8") as f:
    f.write("new entry\n")
```

## pathlib（更现代）

```python
from pathlib import Path

p = Path("data.txt")
p.read_text(encoding="utf-8")
p.write_text("hello", encoding="utf-8")
p.exists()
p.parent
list(Path(".").glob("*.py"))
```

## 异常处理

```python
try:
    num = int(input("输入数字: "))
    result = 10 / num
except ValueError:
    print("不是有效数字")
except ZeroDivisionError:
    print("不能除以零")
except Exception as e:
    print(f"未知错误: {e}")
else:
    print(f"结果: {result}")   # 无异常时
finally:
    print("清理工作")            # 总是执行
```

## 主动抛出

```python
def divide(a, b):
    if b == 0:
        raise ValueError("除数不能为 0")
    return a / b
```

## 自定义异常

```python
class AppError(Exception):
    pass

raise AppError("业务错误")
```

## 模式对照

| 模式 | 说明 |
|------|------|
| `r` | 只读 |
| `w` | 写入（覆盖） |
| `a` | 追加 |
| `rb` / `wb` | 二进制 |

**始终指定 `encoding="utf-8"`**，Windows 默认编码易出乱码。
