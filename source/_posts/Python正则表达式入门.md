---
title: Python 正则表达式入门
date: 2026-08-21 12:15:00
tags:
  - Python
  - 正则
categories:
  - Python 新手入门
---

正则表达式用于**文本模式匹配**，Python 通过 `re` 模块支持。

## 基本用法

```python
import re

text = "联系邮箱: user@example.com 或 admin@test.org"

# 搜索
m = re.search(r"[\w.-]+@[\w.-]+", text)
if m:
    print(m.group())   # user@example.com

# .findall
re.findall(r"[\w.-]+@[\w.-]+", text)
# ['user@example.com', 'admin@test.org']

# 替换
re.sub(r"\d+", "N", "abc123def456")  # "abcNdefN"
```

## 常用元字符

| 模式 | 含义 |
|------|------|
| `.` | 任意字符 |
| `\d` | 数字 |
| `\w` | 字母数字下划线 |
| `\s` | 空白 |
| `[abc]` | a/b/c 之一 |
| `[^abc]` | 非 a/b/c |
| `*` | 0 次或多次 |
| `+` | 1 次或多次 |
| `?` | 0 或 1 次 |
| `{3}` | 恰好 3 次 |
| `^` | 行首 |
| `$` | 行尾 |

## 分组与捕获

```python
m = re.match(r"(\d{4})-(\d{2})-(\d{2})", "2026-08-21")
m.group(1)  # 2026
m.group(2)  # 08
m.groups()  # ('2026', '08', '21')
```

## 编译复用

```python
pattern = re.compile(r"ERROR: (.+)")
for line in log_lines:
    m = pattern.search(line)
    if m:
        print(m.group(1))
```

## 实战：解析日志

```python
line = "192.168.1.1 - - [21/Aug/2026:10:00:00 +0800] \"GET /api HTTP/1.1\" 200"
pat = r"(?P<ip>[\d.]+).*\"(?P<method>\w+) (?P<path>[^ ]+).*\" (?P<status>\d+)"
m = re.search(pat, line)
m.groupdict()
```

## 注意

- 优先用 `str.split()`、`.startswith()` 等简单方法
- 复杂模式用 [regex101.com](https://regex101.com) 调试
- 原始字符串 `r"..."` 避免 `\` 转义混乱

正则强大但难维护，**够用就好**。
