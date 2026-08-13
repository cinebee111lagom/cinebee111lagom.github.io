---
title: vLLM 安装与环境准备入门
date: 2026-09-03 09:30:00
tags:
  - vLLM
  - 安装
  - 入门
categories:
  - vLLM 新手入门
---

vLLM 依赖 **CUDA GPU**，先确认驱动与 PyTorch CUDA 版本匹配。

## 环境检查

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

| 项 | 建议 |
|----|------|
| GPU | Ampere+ 更佳（A10/A100/H100/4090） |
| 驱动 | 满足 CUDA 12.x（以官方为准） |
| Python | 3.9 ~ 3.12 |
| 显存 | 7B ≥ 16GB；13B ≥ 24GB（视精度） |

## pip 安装（常用）

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -U pip
pip install vllm
```

不同 CUDA 版本可能需要指定 wheel，见 [官方安装文档](https://docs.vllm.ai/en/latest/getting_started/installation.html)。

## 验证

```bash
python -c "import vllm; print(vllm.__version__)"
```

## HuggingFace 访问

国内或私网常需：

```bash
export HF_ENDPOINT=https://hf-mirror.com   # 可选镜像
export HF_TOKEN=hf_xxx                     # gated 模型
huggingface-cli login
```

## Docker 快速体验

```bash
docker run --gpus all -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model facebook/opt-125m
```

小模型仅用于连通性测试。

## 反模式

- CPU 版 PyTorch 装上却期望 GPU 加速
- 系统 Python 全局乱装导致冲突
- 显存不够硬上 70B FP16

下一篇：**离线推理快速开始**。
