---
title: SGLang 新手入门：什么是 SGLang 与适用场景
date: 2026-09-05 09:00:00
tags:
  - SGLang
  - LLM
  - 入门
categories:
  - SGLang 新手入门
---

**SGLang**（Structured Generation Language）是面向大模型的高性能推理与服务框架，以 **RadixAttention**、高吞吐服务和 **结构化生成** 见长。

## SGLang 能做什么

| 能力 | 说明 |
|------|------|
| 在线服务 | OpenAI 兼容 HTTP API |
| 离线推理 | Python Runtime 批量生成 |
| 前缀复用 | RadixAttention 共享 KV |
| 结构化输出 | JSON/正则等约束解码 |
| 多模态 | 视觉语言模型推理 |
| 多卡 | Tensor Parallel 等并行 |

## 与同类对比

| | SGLang | vLLM | Ollama |
|---|--------|------|--------|
| 定位 | 高吞吐服务 + 结构化生成 | 高吞吐服务 | 本地易用 |
| 前缀缓存 | RadixAttention 强 | Prefix Caching | 有限 |
| 结构化 | 原生强 | 有约束解码 | 弱 |
| API | OpenAI 兼容 | OpenAI 兼容 | OpenAI 兼容 |

## 适用场景

**适合**：
- 高并发 Chat / Agent 服务
- 大量共享 system prompt / 多轮前缀
- 需要 JSON Schema、正则等结构化输出
- 私有化 LLM 推理平台

**不适合**：
- 仅本机随手试用（Ollama 更简单）
- 训练/全参微调主流程
- 无 GPU 环境

## 学习路线

```
概念 → 安装 → Runtime/Server → 结构化输出 → 多卡/量化 → Docker/K8s → 排查
```

本系列 20 篇从零带你掌握 SGLang 日常使用与推理入门。
