---
title: vLLM 流式输出与 Chat Template 入门
date: 2026-09-03 11:15:00
tags:
  - vLLM
  - 流式
  - 入门
categories:
  - vLLM 新手入门
---

聊天产品几乎都要 **SSE 流式输出**；Instruct 模型必须套对 **Chat Template**。

## OpenAI 流式调用

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

stream = client.chat.completions.create(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[{"role": "user", "content": "讲个短笑话"}],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content or ""
    print(delta, end="", flush=True)
```

## curl 流式

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen2.5-7B-Instruct","messages":[{"role":"user","content":"hi"}],"stream":true}'
```

## Chat Template 是什么

把 `messages` 转成模型训练时见过的字符串格式，例如：

```
<|im_start|>system
You are helpful.<|im_end|>
<|im_start|>user
你好<|im_end|>
<|im_start|>assistant
```

Server 的 `/v1/chat/completions` **自动应用**；`/v1/completions` 则不会。

## 多轮对话

```python
messages = [
    {"role": "system", "content": "你是简洁的助手"},
    {"role": "user", "content": "1+1=?"},
    {"role": "assistant", "content": "2"},
    {"role": "user", "content": "再加 3 呢？"},
]
```

注意 **上下文长度**：历史过长要截断或摘要。

## 反模式

- Chat 模型用 completions 裸 prompt
- 流式前端不处理 `[DONE]`
- system prompt 每次塞进超长文档无管理

下一篇：**LoRA 适配器**。
