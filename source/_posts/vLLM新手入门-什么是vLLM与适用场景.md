---
title: vLLM 新手入门：什么是 vLLM 与适用场景
date: 2026-09-03 09:00:00
tags:
  - vLLM
  - LLM
  - 入门
categories:
  - vLLM 新手入门
---

**vLLM** 是高性能大语言模型推理引擎，以 **PagedAttention** 和 **Continuous Batching** 著称，吞吐常显著高于朴素 Transformers 推理。

## vLLM 能做什么

| 能力 | 说明 |
|------|------|
| 离线推理 | Python API 批量生成 |
| 在线服务 | OpenAI 兼容 HTTP API |
| 高吞吐 | 分页 KV Cache + 连续批处理 |
| 多卡 | Tensor Parallel / Pipeline Parallel |
| 量化 | AWQ、GPTQ、FP8 等 |
| 多模态 | 部分视觉语言模型 |

## 与同类对比

| | vLLM | HuggingFace TGI | Ollama | Transformers |
|---|------|-----------------|--------|--------------|
| 定位 | 生产推理 | 生产推理 | 本地易用 | 研究/开发 |
| 吞吐 | 很高 | 高 | 中 | 低 |
| API | OpenAI 兼容 | HTTP | OpenAI 兼容 | Python |
| 运维 | 中 | 中 | 低 | 低 |

## 适用场景

**适合**：
- 私有化 LLM 推理服务
- 高并发 Chat/Completion API
- 需要最大化 GPU 利用率
- 与 OpenAI SDK 兼容迁移

**不适合**：
- 仅本机玩一玩（Ollama 更简单）
- 训练/微调主战场（用 Trainer/DeepSpeed）
- 无 GPU 环境（需 CPU 方案另议）

## 核心卖点一句话

```
同样一张卡，vLLM 用更好的调度与显存管理 → 更高 QPS、更低成本
```

## 学习路线

```
概念 → 安装 → 离线推理 → OpenAI Server → 多卡/量化 → Docker/K8s → 排查
```

本系列 20 篇从零带你掌握 vLLM 日常使用与推理入门。
