---
title: vLLM 多 GPU 与 Tensor Parallel 入门
date: 2026-09-03 10:45:00
tags:
  - vLLM
  - 多GPU
  - 入门
categories:
  - vLLM 新手入门
---

单卡装不下大模型时，用 **Tensor Parallel（TP）** 把层内计算切到多卡。

## 启动多卡

```bash
# 2 卡
vllm serve Qwen/Qwen2.5-32B-Instruct \
  --tensor-parallel-size 2 \
  --max-model-len 8192

# 4 卡
vllm serve meta-llama/Meta-Llama-3-70B-Instruct \
  --tensor-parallel-size 4
```

```python
llm = LLM(model="...", tensor_parallel_size=2)
```

## 规则与注意

| 点 | 说明 |
|----|------|
| TP 大小 | 通常为 GPU 数，且能整除注意力头等结构 |
| 同机多卡 | NVLink 优于仅 PCIe |
| 可见设备 | `CUDA_VISIBLE_DEVICES=0,1` |
| 显存 | 每卡仍需足够 KV Cache |

## Pipeline Parallel

超大模型还可 **流水并行**（层切到不同卡），延迟与实现更复杂，新手优先 TP。

## 多实例 vs 多卡切一模型

| 策略 | 场景 |
|------|------|
| TP=4 跑 1 个大模型 | 单模型放不下 |
| TP=1 × 4 实例 | 小模型高 QPS（前面加负载均衡） |

```
高并发 7B：4 个独立 vLLM + Nginx
大模型 70B：1 个 vLLM TP=4/8
```

## 验证

```bash
nvidia-smi   # 看多卡是否同时占用
curl localhost:8000/v1/models
```

## 反模式

- TP=3 这类难以整除的配置乱试
- 跨机器当本机 TP（需分布式配置）
- 小模型无脑 TP，通信开销反降吞吐

下一篇：**SamplingParams 采样参数**。
