---
title: SGLang 实战：搭建一个简易 Chat 服务
date: 2026-09-05 13:15:00
tags:
  - SGLang
  - 实战
  - 入门
categories:
  - SGLang 新手入门
---

串联前面知识：启动服务 → 鉴权/调用 → 多轮流式对话。

## 1. 启动

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 30000 \
  --served-model-name chat-7b \
  --context-length 4096 \
  --mem-fraction-static 0.85
```

## 2. 对话脚本

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:30000/v1", api_key="EMPTY")
history = [{"role": "system", "content": "你是简洁的中文助手"}]

while True:
    user = input("You> ").strip()
    if user in {"exit", "quit"}:
        break
    history.append({"role": "user", "content": user})
    stream = client.chat.completions.create(
        model="chat-7b",
        messages=history,
        temperature=0.7,
        max_tokens=512,
        stream=True,
    )
    print("Bot> ", end="")
    answer = []
    for chunk in stream:
        t = chunk.choices[0].delta.content or ""
        answer.append(t)
        print(t, end="", flush=True)
    print()
    history.append({"role": "assistant", "content": "".join(answer)})
```

## 3. 验收清单

- [ ] `/v1/models` 含 `chat-7b`  
- [ ] 流式输出正常  
- [ ] 多轮上下文正常  
- [ ] `nvidia-smi` 有显存占用  
- [ ] 固定 system prompt（利于缓存）  

## 4. 加分项

- 网关 API Key + 限流  
- JSON 结构化抽取小 demo  
- Docker Compose 一键启动  
- `/metrics` 接入 Prometheus  

## 反模式

- history 无限增长撑爆上下文
- 服务裸露到公网

下一篇：**Radix 缓存实践**。
