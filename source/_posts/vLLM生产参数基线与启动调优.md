---
title: vLLM 生产参数基线与启动调优
date: 2026-09-04 09:45:00
tags:
  - vLLM
  - SRE
  - 基线
categories:
  - vLLM SRE
---

生产启动参数应 **版本化、可回滚、分模型档案**。

## 推荐基线（7B 示例）

```bash
vllm serve /models/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name chat-7b \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --max-num-seqs 128 \
  --api-key ${VLLM_API_KEY} \
  --enable-prefix-caching
```

## 参数治理

| 参数 | 生产建议 |
|------|----------|
| max-model-len | 按业务上限，勿盲目 128k |
| gpu-memory-utilization | 0.85~0.92，留 OS/碎片余量 |
| max-num-seqs | 压测后固定，防过载 |
| tensor-parallel-size | 与 GPU 数一致且可整除 |
| api-key | 必须；或前置网关鉴权 |

## 配置即代码

```
configs/
  chat-7b.env
  coder-32b-tp2.env
```

变更走 MR + staging 压测，再推 prod。

## 环境变量

```bash
export CUDA_VISIBLE_DEVICES=0,1
export HF_HUB_OFFLINE=1          # 生产禁用临时下载
export VLLM_API_KEY=***          # 来自 Secret
```

## 反模式

- 生产开 HF 在线拉模型
- 无文档改 max-num-seqs
- 所有模型共用一套参数

基线与压测报告一并归档。
