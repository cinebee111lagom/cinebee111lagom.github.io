---
title: MinIO 与 Ceph RGW、阿里云 OSS 对比入门
date: 2026-09-01 13:00:00
tags:
  - MinIO
  - 对比
  - 入门
categories:
  - MinIO 新手入门
---

选型时常在 **MinIO、Ceph RGW、云 OSS** 之间比较。

## 功能对比

| 维度 | MinIO | Ceph RGW | 阿里云 OSS |
|------|-------|----------|------------|
| 部署复杂度 | 低 | 高 | 无 |
| S3 兼容 | 极好 | 好 | 原生 |
| 块/文件 | ❌ | ✅ | ❌ |
| 边缘/单机 | ✅ | ❌ | ❌ |
| 多租户 | Policy | 多用户 | RAM |
| 成本 | 硬件+人力 | 更高人力 | 按量 |

## 选型建议

```
只要对象、快速上线、团队小     → MinIO
已有 Ceph、块+文件+对象统一    → RGW
公有云、免运维、弹性           → OSS/S3
K8s 备份+应用 S3              → MinIO / OSS
```

## 迁移

| 路径 | 工具 |
|------|------|
| OSS → MinIO | mc mirror / rclone |
| MinIO → OSS | 同上 |
| RGW → MinIO | S3 API 兼容，mc mirror |

```bash
rclone sync oss:mybucket minio:mybucket --progress
```

## 混合架构

```
热数据 MinIO 本地
冷数据 OSS 归档（lifecycle 转存）
```

## 反模式

- 已有成熟 Ceph 再叠 MinIO 无分工
- 小文件海量用对象不加 CDN
- 不评估 egress 费用就全上云

下一篇：**备份迁移**。
