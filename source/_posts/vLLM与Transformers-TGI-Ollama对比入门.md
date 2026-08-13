---
title: vLLM 与 Transformers、TGI、Ollama 对比入门
date: 2026-09-03 13:15:00
tags:
  - vLLM
  - 对比
  - 入门
categories:
  - vLLM 新手入门
---

选型时先问：**本地玩、研究实验、还是生产高并发？**

## 对比表

| 维度 | vLLM | Transformers generate | TGI | Ollama |
|------|------|----------------------|-----|--------|
| 易用性 | 中 | 高 | 中 | 很高 |
| 吞吐 | 很高 | 低 | 高 | 中 |
| 生产 API | 强 | 弱 | 强 | 够用 |
| 多卡 | 强 | 有限 | 强 | 有限 |
| 量化生态 | 强 | 中 | 强 | 强（GGUF） |
| 典型用户 | 平台/SRE | 算法开发 | 平台 | 个人/小团队 |

## 怎么选

```
本机试用、快速跑模型     → Ollama
笔记本写 demo/实验      → Transformers
公司私有化高并发 API    → vLLM 或 TGI
已有 HF 推理栈          → TGI 也可能合适
OpenAI SDK 无缝迁移     → vLLM 很合适
```

## 迁移提示

从 OpenAI 云到 vLLM：改 `base_url` 即可。  
从 Ollama 到 vLLM：模型格式与参数名需重配，重点测质量与延迟。

## 反模式

- 用 Transformers 裸 generate 硬抗生产流量
- 用 Ollama 顶核心交易链路却无 SLA
- 同时维护三套推理栈无标准

下一篇：**实战简易 Chat 服务**。
