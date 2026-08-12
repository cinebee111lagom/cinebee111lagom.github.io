---
title: Python 网络请求：requests 入门
date: 2026-08-21 12:30:00
tags:
  - Python
  - requests
  - HTTP
categories:
  - Python 新手入门
---

`requests` 是 Python 最流行的 HTTP 库，调用 API 必备。

## 安装

```bash
pip install requests
```

## GET 请求

```python
import requests

resp = requests.get("https://httpbin.org/get", params={"q": "python"})
resp.status_code      # 200
resp.text             # 响应文本
resp.json()           # JSON 解析
resp.headers
resp.raise_for_status()  # 非 2xx 抛异常
```

## POST 请求

```python
# JSON body
resp = requests.post(
    "https://httpbin.org/post",
    json={"name": "旺仔", "age": 25},
    headers={"Authorization": "Bearer token"},
    timeout=10,
)

# 表单
resp = requests.post(url, data={"key": "value"})

# 文件上传
files = {"file": open("report.pdf", "rb")}
resp = requests.post(url, files=files)
```

## Session（保持 Cookie）

```python
session = requests.Session()
session.get("https://example.com/login")
session.post("https://example.com/login", data={"user": "a", "pass": "b"})
session.get("https://example.com/dashboard")
```

## 异常处理

```python
try:
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
except requests.Timeout:
    print("超时")
except requests.HTTPError as e:
    print(f"HTTP 错误: {e}")
except requests.RequestException as e:
    print(f"请求失败: {e}")
```

## 下载文件

```python
resp = requests.get(url, stream=True)
with open("file.zip", "wb") as f:
    for chunk in resp.iter_content(chunk_size=8192):
        f.write(chunk)
```

## 最佳实践

- 始终设 `timeout`
- 用 `raise_for_status()` 或检查 status_code
- API Key 放环境变量，不要硬编码
- 高并发用 `httpx` + async 或专用客户端

requests 让 HTTP 调用像读本地文件一样简单。
