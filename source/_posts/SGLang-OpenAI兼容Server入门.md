---
title: SGLang OpenAI 兼容 Server 入门
date: 2026-09-05 10:00:00
tags:
  - SGLang
  - API
  - 入门
categories:
  - SGLang 新手入门
---

生产最常用：启动 **OpenAI Compatible Server**，用官方 SDK 调用。

## 启动服务

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 30000 \
  --dtype auto
```

## Chat Completions

```bash
curl http://localhost:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "用三句话介绍 SGLang"}],
    "temperature": 0.7,
    "max_tokens": 200
  }'
```

## Python OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:30000/v1",
    api_key="EMPTY",
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
| `/v1/models` | 模型列表 |
| `/v1/chat/completions` | 对话 |
| `/v1/completions` | 补全 |
| `/health` | 健康检查（若启用） |

## 常用启动参数

| 参数 | 说明 |
|------|------|
| `--tp-size` | 多卡 |
| `--mem-fraction-static` | 显存比例 |
| `--context-length` | 上下文上限 |
| `--served-model-name` | 对外模型名 |
| `--api-key` | 简单鉴权（视版本） |

## 反模式

- 公网裸奔无鉴权
- model 字段与启动名不一致
- 忘记 `--host 0.0.0.0` 导致容器外不可达

下一篇：**采样参数**。
