---
title: MinIO 容量规划与磁盘治理
date: 2026-09-02 11:15:00
tags:
  - MinIO
  - SRE
  - 容量
categories:
  - MinIO SRE
---

对象存储容量 **只增不减** 是常态，需 lifecycle + 配额 + 扩容流程。

## 容量公式

```
可用 ≈ 原始磁盘 × EC 效率 × (1 - 预留 15%)
```

```bash
mc admin info alias
# Usable / Raw 比例监控
```

## 治理手段

| 手段 | 适用 |
|------|------|
| lifecycle 过期 | 日志/tmp |
| versioning 非当前版本清理 | 版本桶 |
| bucket quota | 租户 |
| 分桶 | 业务隔离 |

```bash
mc quota set alias/logs --size 500GB
mc ilm ls alias/logs
```

## 扩容

```
1. 加节点/加盘（符合 erasure set 规则）
2. 或新 pool Tenant（K8s）
3. mc admin info 验证
4. 观察 heal/rebalance
```

## 周报

- Top 10 bucket 容量
- 增长率预测耗尽日期
- 无 lifecycle 的大桶清单

## 反模式

- 90% 才行动
- versioning 无 NoncurrentExpiration
- 单 bucket 无限增长

**可用 < 20% 必须工单+扩容计划**。
