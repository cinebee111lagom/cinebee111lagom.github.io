---
title: SGLang 流式输出与多轮对话入门
date: 2026-09-05 10:30:00
tags:
  - SGLang
  - 流式
  - 入门
categories:
  - SGLang 新手入门
---

聊天产品几乎都要 **SSE 流式**；多轮要管好 **历史长度与前缀复用**。

## OpenAI 流式

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:30000/v1", api_key="EMPTY")

stream = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[{"role": "user", "content": "讲个短笑话"}],
    stream=True,
)

for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

## 多轮对话

```python
messages = [
    {"role": "system", "content": "你是简洁的助手"},
    {"role": "user", "content": "1+1=?"},
    {"role": "assistant", "content": "2"},
    {"role": "user", "content": "再加 3?"},
]
```

注意：

- 历史过长要截断或摘要  
- 固定 system prompt 有利于 **RadixAttention** 命中  
- Chat 接口会应用 chat template  

## 流式注意点

| 点 | 说明 |
|----|------|
| 代理缓冲 | Nginx 需关闭 buffering |
| 超时 | 长生成要加大 read timeout |
| 取消 | 客户端断开后服务端应尽快停止 |

## 反模式

- 每轮把整个知识库塞进 system，长度爆炸
- 用 completions 裸拼 Chat 模板导致格式错乱
- 流式前端不处理结束事件

下一篇：**结构化输出**。
