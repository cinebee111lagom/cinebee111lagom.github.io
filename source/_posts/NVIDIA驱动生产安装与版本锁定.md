---
title: NVIDIA 驱动生产安装与版本锁定
date: 2026-08-25 09:30:00
tags:
  - nvidia-smi
  - SRE
  - 驱动
categories:
  - nvidia-smi SRE
---

驱动是 GPU 节点一切能力的根基。SRE 必须**统一版本、可回滚、可验证**。

## 版本策略

| 原则 | 说明 |
|------|------|
| 池内一致 | 同一 GPU 池同一 driver + CUDA 兼容线 |
| 滞后稳定 | 生产比最新版晚 1~2 个季度 |
| 矩阵文档 | Driver ↔ CUDA ↔ 框架（PyTorch/TF）对照表 |
| 变更窗口 | 低峰 + 逐节点滚动 |

## 安装后验收

```bash
nvidia-smi
nvidia-smi --query-gpu=driver_version,cuda_version --format=csv
modinfo nvidia | grep ^version
lsmod | grep nvidia
```

期望：`nvidia-smi` 无报错，所有 GPU 可见，驱动版本与基线一致。

## 生产安装要点（Linux）

```bash
# 禁用 nouveau（若裸金属）
# 使用 runfile 或 distro 包，团队内固定一种
# 安装后开启持久化模式（训练节点推荐）
sudo nvidia-smi -pm 1
```

## 版本锁定手段

- **Ansible role** 固定 package 版本
- **Golden AMI** 预装驱动，变更发新 AMI
- **K8s** 节点镜像 pin 驱动，禁止 apt upgrade 漂移

## 变更 Runbook 摘要

1. 在 staging 节点验证驱动 + 典型训练/推理作业
2.  cordon 单节点 →  drain 作业 → 升级 → `nvidia-smi` 验收
3. 观察 24h XID/ECC → 推广至全池

## 反模式

- 生产节点 `apt upgrade` 自动升级驱动
- 不记录 `driver_version` 到 CMDB
- 升级后未跑 `nvidia-smi -L` 即接流量

驱动变更前后各执行一次 **nvidia-smi 全量 query**，留存审计。
