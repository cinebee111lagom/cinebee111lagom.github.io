---
title: MinIO 生产部署架构选型指南
date: 2026-09-02 09:15:00
tags:
  - MinIO
  - SRE
  - 架构
categories:
  - MinIO SRE
---

MinIO 生产架构在 **裸金属分布式、K8s Operator、边缘单集群** 间选型。

## 部署模式

| 模式 | 优点 | 缺点 | 适用 |
|------|------|------|------|
| 裸金属分布式 | 性能最优 | 需自备 LB | 大规模生产 |
| VM 分布式 | 弹性 | 性能损耗 | 私有云 |
| K8s Operator Tenant | 云原生 | 存储路径复杂 | K8s 为主环境 |
| 单节点 | 简单 | 无冗余 | 仅 dev |

## 最小生产分布式

```
4 节点 × 4 盘 = 16 drives
EC 自动布局，容忍多块盘故障
前接 Nginx/HAProxy LB ×2
Console 与 API 分域名
```

## 网络

| 平面 | 建议 |
|------|------|
| Client → LB | 25Gb/10Gb |
| 节点间 | 独立复制网（同 DC） |
| DNS | api.minio.example.com |

## 与 Ceph RGW / OSS

| 场景 | 选型 |
|------|------|
| 纯 S3、快速 | MinIO |
| 块+文件+对象 | Ceph |
| 免运维 | 云 OSS |

## Tenant 规划

```
prod-assets    → 业务静态资源
backup-velero  → K8s 备份
logs-archive   → lifecycle 90d
ml-datasets    → 大对象 EC
```

## 反模式

- 生产单机
- 2 节点「伪分布式」
- 无 LB 绑单节点

选型文档含：**容量 3 年、IOPS、RPO/RTO、合规**。
