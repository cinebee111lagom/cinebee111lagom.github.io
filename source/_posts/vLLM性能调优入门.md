---
title: vLLM 性能调优入门
date: 2026-09-03 12:45:00
tags:
  - vLLM
  - 性能
  - 入门
categories:
  - vLLM 新手入门
---

调优目标通常是：**更高吞吐（token/s）** 或 **更低延迟（TTFT）**，二者常需权衡。

## 关键旋钮

| 参数 | 影响 |
|------|------|
| `max_model_len` | 越小 KV 越省，并发越高 |
| `gpu_memory_utilization` | 提高可增 KV，但易 OOM |
| `max_num_seqs` | 最大并发序列数 |
| `max_num_batched_tokens` | 每步批处理 token 上限 |
| 量化 | 省显存换精度 |
| 前缀缓存 | 重复系统提示提速 |

```bash
vllm serve MODEL \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 128
```

## 延迟 vs 吞吐

| 目标 | 做法 |
|------|------|
| 低延迟 | 降并发、小 batch、足够 GPU |
| 高吞吐 | 提高并发、continuous batching 吃满 GPU |

## 压测思路

```bash
# 用官方 benchmark 或自写脚本
# 记录：QPS、TTFT P50/P99、输出 token/s、GPU 利用率
```

固定：**模型、长度分布、采样参数**，只改一个旋钮。

## 输入输出长度

- 长 prompt → 预填（prefill）重，TTFT 升  
- 长生成 → 解码阶段占时间  
- 业务上能截断上下文就截断  

## 反模式

- 无基线就「感觉慢」
- max_model_len=128k 服务短聊天
- 同时开满所有激进参数导致频繁 OOM

下一篇：**常见问题与排查**。
