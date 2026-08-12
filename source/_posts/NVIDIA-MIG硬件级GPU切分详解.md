---
title: NVIDIA MIG：硬件级 GPU 切分详解
date: 2026-08-13 09:30:00
tags:
  - GPU切分
  - MIG
  - NVIDIA
categories:
  - GPU切分
---

**MIG（Multi-Instance GPU）** 是 NVIDIA Ampere 及更新架构（A100、A30、H100 等）提供的**硬件级** GPU 切分方案。

## 工作原理

MIG 在 GPU 内部划分：

- 独立的 **SM（流多处理器）** 子集
- 独立的 **显存** 分区
- 独立的 **L2 缓存** 份额
- 独立的 **NVDEC/NVENC** 引擎访问（视 profile 而定）

各实例之间**硬件隔离**，一实例 OOM 不影响其他实例。

## A100 80GB 常见 profile

| Profile | 显存 | 最大实例数 |
|---------|------|------------|
| `1g.10gb` | 10 GB | 7 |
| `2g.20gb` | 20 GB | 3 |
| `3g.40gb` | 40 GB | 2 |
| `7g.80gb` | 80 GB | 1（整卡） |

```bash
# 查看 MIG 状态
nvidia-smi -L
nvidia-smi mig -lgi
```

## 配置示例

```bash
# 启用 MIG 模式（需 root，重启 GPU 后生效）
sudo nvidia-smi -mig 1

# 创建 7 个 1g.10gb 实例
sudo nvidia-smi mig -cgi 19,19,19,19,19,19,19 -C
```

## 限制

- Profile **静态配置**，变更需销毁重建实例
- 仅部分 GPU 型号支持（消费级 RTX 不支持 MIG）
- 单实例算力有上限，大模型训练仍需整卡或 7g profile

MIG 是**生产多租户推理**的首选硬件切分方案。
