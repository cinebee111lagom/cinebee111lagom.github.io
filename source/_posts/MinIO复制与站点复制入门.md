---
title: MinIO 复制与站点复制入门
date: 2026-09-01 11:30:00
tags:
  - MinIO
  - 复制
  - 入门
categories:
  - MinIO 新手入门
---

MinIO 提供 **桶级主动复制** 与 **站点复制（Site Replication）** 做灾备。

## 桶级主动复制（Bucket Replication）

```bash
# 目标集群 alias
mc alias set remote http://dr-minio:9000 admin 'pass'

# 添加规则
mc replicate add local/mybucket \
  --remote-bucket remote/mybucket \
  --priority 1 \
  --replicate "delete,delete-marker,existing-objects"
```

新对象自动异步复制到 DR 集群。

## 站点复制（多站点全集群）

适用于 **多个 MinIO 集群** 配置级同步（用户、bucket 元数据等）：

```bash
mc admin replicate add site1 site2
mc admin replicate info site1
```

需 MinIO 企业级功能或特定版本，生产前查官方文档。

## 单向 vs 双向

| 模式 | 适用 |
|------|------|
| 单向 | 生产 → DR |
| 双向 | 多活（冲突需应用层处理） |

## mc mirror 一次性同步

```bash
mc mirror local/mybucket remote/mybucket
```

适合 **初始全量**，非持续复制。

## 验证

```bash
mc replicate backlog local/mybucket
mc admin replicate status site1
```

## 反模式

- 无监控 replication lag
- 双向复制 + 同名 key 并发写
- DR 从未演练恢复

下一篇：**TLS**。
