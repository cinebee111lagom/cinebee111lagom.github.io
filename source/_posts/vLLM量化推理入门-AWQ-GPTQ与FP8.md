---
title: vLLM 量化推理入门：AWQ、GPTQ 与 FP8
date: 2026-09-03 10:30:00
tags:
  - vLLM
  - 量化
  - 入门
categories:
  - vLLM 新手入门
---

量化用更低精度存权重，**省显存、提吞吐**，略损精度。

## 常见方案

| 方案 | 特点 | 适用 |
|------|------|------|
| AWQ | 4bit，质量较好 | 消费卡/边缘 |
| GPTQ | 4bit，生态成熟 | 显存紧张 |
| FP8 | 新卡加速好 | Hopper/Ada 等 |
| INT8 | 折中 | 部分场景 |

## 加载 AWQ 模型

```bash
vllm serve TheBloke/Mistral-7B-Instruct-v0.2-AWQ \
  --quantization awq \
  --dtype auto
```

```python
llm = LLM(model="TheBloke/xxx-AWQ", quantization="awq")
```

## GPTQ

```python
llm = LLM(model="TheBloke/xxx-GPTQ", quantization="gptq")
```

## FP8（示意）

```bash
vllm serve meta-llama/Meta-Llama-3-8B-Instruct \
  --quantization fp8
```

以当前版本支持为准。

## 选型建议

```
显存够用、要最好质量 → BF16/FP16
显存紧、7B/14B 上 24GB → AWQ/GPTQ
新卡追求吞吐 → FP8
```

## 质量与速度

| 精度 | 显存 | 速度 | 质量 |
|------|------|------|------|
| BF16 | 高 | 基线 | 最好 |
| FP8 | 中 | 快 | 接近 |
| INT4 | 低 | 通常更快 | 略降 |

## 反模式

- 未量化权重却传 `--quantization awq`
- 把量化当「无损压缩」
- 评测只看速度不看任务指标

下一篇：**多 GPU Tensor Parallel**。
