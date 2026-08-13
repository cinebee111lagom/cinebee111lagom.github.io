---
title: SGLang 多 GPU 与 Tensor Parallel 入门
date: 2026-09-05 11:00:00
tags:
  - SGLang
  - 多GPU
  - 入门
categories:
  - SGLang 新手入门
---

单卡装不下时，用 **Tensor Parallel（TP）** 把模型切到多卡。

## 启动多卡

```bash
python -m sglang.launch_server \
  --model-path Qwen/Qwen2.5-32B-Instruct \
  --tp-size 2 \
  --host 0.0.0.0 \
  --port 30000
```

```bash
# 指定可见卡
CUDA_VISIBLE_DEVICES=0,1 python -m sglang.launch_server \
  --model-path /models/llama-70b \
  --tp-size 4
```

## 选择策略

| 策略 | 场景 |
|------|------|
| TP=N 单实例 | 大模型放不下 |
| TP=1 × 多副本 | 小模型高 QPS（前面加 LB） |

## 注意

| 点 | 说明 |
|----|------|
| 卡间互联 | NVLink 优于纯 PCIe |
| 整除约束 | 头数等结构通常需可被 TP 整除 |
| 显存 | 每卡仍需 KV Cache 空间 |
| 故障域 | TP 一组卡绑在一起，单卡挂可能整实例挂 |

## 验证

```bash
nvidia-smi
curl http://localhost:30000/v1/models
```

## 反模式

- 小 7B 无脑 TP=8，通信开销伤吞吐
- 跨机器硬当本机 TP
- 不设 CUDA_VISIBLE_DEVICES 抢错卡

下一篇：**量化**。
