---
title: SGLang 安装与环境准备入门
date: 2026-09-05 09:30:00
tags:
  - SGLang
  - 安装
  - 入门
categories:
  - SGLang 新手入门
---

SGLang 依赖 **CUDA GPU** 与匹配的 PyTorch，先确认驱动与显卡。

## 环境检查

```bash
nvidia-smi
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

| 项 | 建议 |
|----|------|
| GPU | Ampere+ 更佳 |
| Python | 3.9+（以官方为准） |
| 显存 | 7B ≥ 16GB；更大模型需更多或 TP |

## pip 安装

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -U pip
pip install "sglang[all]"
```

不同 CUDA 版本可能需按 [官方安装文档](https://docs.sglang.ai/) 选择索引或预编译包。

## 验证

```bash
python -c "import sglang; print('ok')"
# 或查看 CLI
python -m sglang.launch_server --help | head
```

## HuggingFace

```bash
export HF_TOKEN=hf_xxx
# 可选镜像
export HF_ENDPOINT=https://hf-mirror.com
```

## Docker（可选）

```bash
docker run --gpus all -p 30000:30000 \
  --shm-size 32g \
  lmsysorg/sglang:latest \
  python -m sglang.launch_server \
  --model-path facebook/opt-125m \
  --host 0.0.0.0 \
  --port 30000
```

小模型仅用于连通性测试。

## 反模式

- CPU 版 PyTorch 期望 GPU 加速
- shm 过小导致多进程异常
- 显存不够硬上 70B

下一篇：**离线 Runtime 快速开始**。
