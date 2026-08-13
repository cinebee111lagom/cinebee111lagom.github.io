---
title: vLLM LoRA 适配器入门
date: 2026-09-03 11:30:00
tags:
  - vLLM
  - LoRA
  - 入门
categories:
  - vLLM 新手入门
---

**LoRA** 用小适配器改模型行为，无需加载多份全量权重，适合多租户个性化。

## 启用 LoRA

```bash
vllm serve meta-llama/Meta-Llama-3-8B-Instruct \
  --enable-lora \
  --max-loras 4 \
  --max-lora-rank 64
```

## 请求时指定适配器

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sql-lora",
    "messages": [{"role": "user", "content": "把用户表查出来"}],
    "max_tokens": 200
  }'
```

需先把 LoRA 注册为 served model（通过启动参数或动态加载，视版本）。

## 启动时挂载示例

```bash
vllm serve base-model \
  --enable-lora \
  --lora-modules sql-lora=/path/to/lora_adapter
```

## 适用场景

| 场景 | 说明 |
|------|------|
| 多业务风格 | 客服 / 代码 / 法务各一个 LoRA |
| 省显存 | 共享 base，热插拔适配器 |
| A/B | 同一服务切换不同 LoRA |

## 注意

- LoRA 需与 **base 架构匹配**
- `max_loras`、`max_lora-rank` 影响显存
- 不是所有量化组合都支持 LoRA

## 反模式

- base 与 LoRA 版本不一致
- 把全量微调目录当 LoRA 路径
- 无上限加载几十个 LoRA 导致 OOM

下一篇：**多模态入门**。
