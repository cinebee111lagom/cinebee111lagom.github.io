---
title: vLLM 实战：搭建一个简易 Chat 服务
date: 2026-09-03 13:30:00
tags:
  - vLLM
  - 实战
  - 入门
categories:
  - vLLM 新手入门
---

把前面知识串起来：启动服务 → 鉴权 → 简单前端/脚本对话。

## 1. 启动

```bash
export VLLM_API_KEY=sk-demo-change-me

vllm serve Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --api-key $VLLM_API_KEY \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --served-model-name chat-7b
```

## 2. 对话脚本

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="sk-demo-change-me",
)

history = [{"role": "system", "content": "你是简洁的中文助手"}]

while True:
    user = input("You> ").strip()
    if user in {"exit", "quit"}:
        break
    history.append({"role": "user", "content": user})
    resp = client.chat.completions.create(
        model="chat-7b",
        messages=history,
        temperature=0.7,
        max_tokens=512,
        stream=True,
    )
    print("Bot> ", end="")
    answer = []
    for chunk in resp:
        t = chunk.choices[0].delta.content or ""
        answer.append(t)
        print(t, end="", flush=True)
    print()
    history.append({"role": "assistant", "content": "".join(answer)})
```

## 3. 最小验收

- [ ] `/health` 200  
- [ ] `/v1/models` 含 `chat-7b`  
- [ ] 错误 api-key 被拒绝  
- [ ] 多轮上下文正常  
- [ ] `nvidia-smi` 有显存占用  

## 4. 下一步可加

- Nginx 限流与 TLS  
- 系统提示词与敏感词过滤  
- Prometheus 抓 metrics  
- Docker Compose 一键启动  

## 反模式

- 无 api-key 暴露到办公网
- history 无限增长撑爆上下文

这是入门综合练习，打通后再看 SRE 系列做生产化。
