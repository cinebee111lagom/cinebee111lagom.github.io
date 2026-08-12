---
title: GitLab 性能调优与容量规划
date: 2026-08-29 13:15:00
tags:
  - GitLab
  - SRE
  - 容量
categories:
  - GitLab SRE
---

容量规划需同时看 **Web、Git、CI、Registry** 四条负载线。

## 容量维度

| 维度 | 信号 | 扩容 |
|------|------|------|
| Web | HTTP P99、Puma CPU | 加 App 节点 |
| Git | Gitaly latency、磁盘 | Gitaly 节点/SSD |
| CI | Job 排队、Runner CPU | 加 Runner |
| Sidekiq | queue size | 加 sidekiq 并发/节点 |
| PG | 连接数、慢查询 | 升配/PgBouncer |

## 估算（粗算）

```
Concurrent CI jobs × (2 CPU, 4Gi) = Runner 资源
Daily active users × 50MB ≈ Redis cache 参考
Repo 总大小 × 1.3 = Gitaly 磁盘（含 growth）
```

## 性能调优清单

- [ ] 对象存储 offload artifacts/LFS/uploads
- [ ] Registry 走 S3 + cleanup
- [ ] Puma/Sidekiq worker 数匹配 CPU
- [ ] Git 大仓 LFS 化
- [ ] CI cache S3 共享
- [ ] PostgreSQL 索引/ vacuum 正常

## 压测

- `gitlab-rake load_balancer:health`
- 模拟并发 clone：`git clone` 并行脚本
- CI：多项目同时 trigger pipeline

## 降级策略

| 压力 | 降级 |
|------|------|
| Sidekiq 积压 | 暂停 Pipeline schedule |
| 磁盘紧急 | 加速 Registry GC |
| CI 过载 | 限 concurrent、非 urgent 排队 |

## 反模式

- 只扩 CPU 不看 Gitaly 磁盘
- 无容量周报
- Runner 无 limit 打满集群

容量评审 **季度**，含 Pipeline 增长趋势。
