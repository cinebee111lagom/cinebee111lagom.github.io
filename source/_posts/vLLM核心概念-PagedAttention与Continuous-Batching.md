---
title: vLLM 核心概念：PagedAttention 与 Continuous Batching
date: 2026-09-03 09:15:00
tags:
  - vLLM
  - 入门
categories:
  - vLLM 新手入门
---

理解两个核心概念，才能明白 vLLM **为什么快**。

## KV Cache 问题

Transformer 解码时要缓存每层 **Key/Value**。传统实现常按「最大长度 × 最大 batch」预分配，导致：

| 问题 | 结果 |
|------|------|
| 显存碎片 | 用不完也占着 |
| 预留过大 | 并发上不去 |
| 批处理僵硬 | 长短请求互相拖累 |

## PagedAttention

类似操作系统分页：把 KV Cache 切成 **固定大小的 page**，按需分配、按需回收。

```
请求 A：占用 page 1,3,5
请求 B：占用 page 2,4
空闲 page 可立刻给新请求
```

| 收益 | 说明 |
|------|------|
| 更高并发 | 显存利用率显著提升 |
| 更少浪费 | 不必按最长序列预留 |
| 共享前缀 | 相同 prompt 前缀可共享（进阶） |

## Continuous Batching（连续批处理）

传统 batch：等整批都跑完再接下一批。

vLLM：**某个请求一结束，立刻塞进新请求**，GPU 几乎不停。

```
时间 →
Batch: [Req1████][Req2██][Req3██████]
       结束即替换新请求，无需等待最长那个
```

## 其他关键概念

| 概念 | 含义 |
|------|------|
| Tensor Parallel | 模型切到多卡 |
| max_model_len | 最大上下文长度 |
| gpu_memory_utilization | 预留显存比例（默认约 0.9） |
| SamplingParams | temperature、top_p 等 |

## 反模式

- 把 max_model_len 开到模型上限却只跑短对话（浪费 KV）
- gpu_memory_utilization=1.0 导致 OOM
- 不懂 continuous batching 却抱怨「单请求也不快」

下一篇：**环境与安装**。
