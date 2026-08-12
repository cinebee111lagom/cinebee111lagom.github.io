---
title: CUDA MPS：软件级 GPU 时间片切分
date: 2026-08-13 10:30:00
tags:
  - GPU切分
  - MPS
  - CUDA
categories:
  - GPU切分
---

**MPS（Multi-Process Service）** 允许多个 CUDA 进程**共享同一 GPU Context**，减少切换开销，实现轻量级时间片共享。

## 工作机制

```
默认模式：进程 A Context ↔ 进程 B Context（切换开销大）

MPS 模式：进程 A ─┐
                  ├→ MPS Server → 单一 Context → GPU
          进程 B ─┘
```

MPS Server 作为代理，合并客户端提交的内核到同一 Context。

## 启动 MPS

```bash
# 启动 MPS 守护进程
nvidia-cuda-mps-control -d

# 客户端进程正常跑 CUDA，自动走 MPS
python train.py &
python infer.py &
```

## 优缺点

| 优点 | 缺点 |
|------|------|
| 配置简单，无需 MIG | **无显存隔离** |
| 多进程 SM 利用率高 | 一进程 OOM 拖垮全部 |
| 适合开发调试 | 不适合严格 SLA 多租户 |

## 适用场景

- 多个小推理服务共享一张 T4
- CI 并行跑 GPU 单元测试
- 研究环境多人共享开发卡

## 与 MIG 组合

**不要**在同一 GPU 上混用 MIG 实例内 MPS 多租户——MIG 实例已是隔离单元，实例内单进程即可。

MPS 是**最轻量**的切分方式，牺牲隔离换灵活。
