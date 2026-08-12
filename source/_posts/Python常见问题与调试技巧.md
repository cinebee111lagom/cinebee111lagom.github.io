---
title: Python 常见问题与调试技巧
date: 2026-08-21 13:30:00
tags:
  - Python
  - 调试
categories:
  - Python 新手入门
---

新手常踩的坑和实用调试方法汇总。

## 常见错误

### IndentationError

```python
# 缩进不一致（空格 vs Tab）
if True:
print("wrong")   # 报错
```

统一 4 空格，IDE 设「空格代替 Tab」。

### NameError / AttributeError

```python
print(undefined_var)   # NameError
"".append(1)           # AttributeError（str 无 append）
```

检查变量名拼写、对象类型。

### TypeError

```python
"1" + 1   # str 和 int 不能相加
int("abc")  # 无效转换
```

用 `type()` 或 IDE 提示确认类型。

### IndexError / KeyError

```python
lst[999]        # IndexError
d["missing"]    # KeyError，改用 d.get("missing")
```

### 可变默认参数陷阱

```python
# 错误
def append_item(item, lst=[]):
    lst.append(item)
    return lst

# 正确
def append_item(item, lst=None):
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

## 调试工具

### print 调试

```python
print(f"debug: x={x}, type={type(x)}")
```

### pdb 断点

```python
import pdb; pdb.set_trace()   # 旧写法
breakpoint()                   # Python 3.7+
```

### 日志（优于 print）

```python
import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
log.debug("变量 x=%s", x)
```

## IDE 调试

VS Code / PyCharm：打断点 → F5 启动 → 单步、查看变量。

## 性能粗查

```python
import time
start = time.time()
# 代码
print(time.time() - start)

# 或
python -m cProfile script.py
```

## 求助前 checklist

- [ ] 读完整 traceback（从下往上看）
- [ ] 最小复现代码
- [ ] 查官方文档 / Stack Overflow
- [ ] 检查 Python 版本和依赖版本

**报错信息是线索，不是敌人**。
