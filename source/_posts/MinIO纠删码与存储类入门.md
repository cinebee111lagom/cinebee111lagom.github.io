---
title: MinIO 纠删码与存储类入门
date: 2026-09-01 12:45:00
tags:
  - MinIO
  - 纠删码
  - 入门
categories:
  - MinIO 新手入门
---

MinIO 分布式默认 **纠删码（Erasure Coding）** 保护数据，理解 EC 才能规划容量与容错。

## Erasure Code 概念

```
N 个数据块 + M 个校验块
可容忍最多 M 块盘/节点故障（视布局）
空间利用率 ≈ N / (N+M)
```

MinIO 根据 **drive 数量自动选择** EC 布局。

## 查看布局

```bash
mc admin info local
# 显示 Erasure sets, parity 等
```

## 存储类（Storage Class）

| 类 | 说明 |
|----|------|
| STANDARD | 默认 |
| REDUCED_REDUNDANCE | 较低冗余（若启用） |

上传时指定：

```bash
aws --endpoint-url http://localhost:9000 s3 cp file.txt s3://bucket/ --storage-class REDUCED_REDUNDANCE
```

## 容量规划

```
可用容量 ≈ 原始磁盘总容量 × EC 效率
预留 10~15% 空闲应对 rebuild
```

## 与副本对比（Ceph 三副本）

| | MinIO EC | 3 副本 |
|---|----------|--------|
| 空间效率 | 高 | 33% |
| 恢复 | rebuild 条带 | 复制 |

## 反模式

- 磁盘 < 4 块强行分布式
- 满盘运行无预留
- 不懂 parity 以为可丢一半节点

下一篇：**与 Ceph/OSS 对比**。
