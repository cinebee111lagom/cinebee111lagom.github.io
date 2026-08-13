---
title: SGLang 与 vLLM、TGI、Ollama 对比入门
date: 2026-09-05 12:45:00
tags:
  - SGLang
  - 对比
  - 入门
categories:
  - SGLang 新手入门
---

选型先看：**本地试用、生产高并发、还是强结构化输出？**

## 对比表

| 维度 | SGLang | vLLM | TGI | Ollama |
|------|--------|------|-----|--------|
| 易用性 | 中 | 中 | 中 | 很高 |
| 吞吐 | 很高 | 很高 | 高 | 中 |
| 前缀缓存 | Radix 强 | 强 | 有 | 有限 |
| 结构化生成 | 很强 | 有 | 有 | 弱 |
| OpenAI API | 有 | 有 | 有 | 有 |
| 典型用户 | 平台/Agent | 平台 | HF 生态 | 个人 |

## 怎么选

```
本机快速试用           → Ollama
私有化高并发 Chat      → SGLang 或 vLLM
大量共享前缀 / Agent   → 优先评估 SGLang
已有 vLLM 平台成熟     → 可继续 vLLM，按需并行 POC
HF 推理栈              → TGI 也可能合适
```

## 迁移提示

- OpenAI SDK：改 `base_url` 即可试  
- 重点回归：流式、工具调用、结构化成功率、TTFT  
- 不要只在单请求延迟上对比  

## 反模式

- 无压测无评测集就全量替换引擎
- 同时维护三套栈无标准

下一篇：**常见问题排查**。
