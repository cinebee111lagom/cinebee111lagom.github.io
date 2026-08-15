---
title: Dragonfly Helm Charts 安装入门
date: 2026-09-07 10:00:00
tags:
  - Dragonfly
  - Helm
  - 入门
categories:
  - Dragonfly 新手入门
---

生产推荐用官方 **Helm Charts** 安装 Dragonfly。

## 常见开关

| 配置 | 含义 |
|------|------|
| 轻量 vs Manager | 是否启用 manager/mysql |
| redis.enable / externalRedis | 持久化 Task 所需 |
| Seed Peer / Peer 副本与磁盘 | 容量关键 |
| 镜像仓库与拉取密钥 | 空气间隙环境 |

## 流程

1. 添加 chart 仓库并拉取 values
2. 按部署模型裁剪 values
3. helm install/upgrade
4. 检查 Pod Ready 与 Service

## 提示

- values 入库 Git，禁止只改集群不改仓库
- 升级前读 chart Release Note

> 官方文档：[Helm Charts](https://d7y.io/docs/next/getting-started/installation/helm-charts/)

