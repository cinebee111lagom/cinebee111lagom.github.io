---
title: vLLM OpenAI 兼容 API Server 入门
date: 2026-09-03 10:00:00
tags:
  - vLLM
  - API
  - 入门
categories:
  - vLLM 新手入门
---

生产最常见用法：启动 **OpenAI Compatible Server**，用官方 SDK 调用。

## 启动服务

```bash
vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype auto \
  --max-model-len 8192
```

旧写法仍常见：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --port 8000
```

## 调用 Chat Completions

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "用三句话介绍 vLLM"}],
    "temperature": 0.7,
    "max_tokens": 200
  }'
```

## Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",  # vLLM 默认可不校验
)

resp = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[{"role": "user", "content": "Hello"}],
)
print(resp.choices[0].message.content)
```

## 常用端点

| 路径 | 用途 |
|------|------|
| `/v1/models` | 列出模型 |
| `/v1/chat/completions` | 对话 |
| `/v1/completions` | 补全 |
| `/health` | 健康检查 |

## 常用启动参数

| 参数 | 说明 |
|------|------|
| `--api-key` | 启用简单鉴权 |
| `--tensor-parallel-size` | 多卡 |
| `--served-model-name` | 对外模型名 |
| `--enable-prefix-caching` | 前缀缓存（进阶） |

## 反模式

- 公网裸奔无鉴权
- model 字段与启动模型名不一致导致 404
- 忘记 `--host 0.0.0.0` 导致容器外访问失败

下一篇：**模型加载与 HuggingFace**。
