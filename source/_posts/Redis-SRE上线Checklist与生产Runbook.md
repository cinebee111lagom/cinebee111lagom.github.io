---
title: Redis SRE 上线 Checklist 与生产 Runbook
date: 2026-08-13 18:45:00
tags:
  - Redis
  - SRE
  - Runbook
categories:
  - Redis SRE
---

本篇汇总 Redis 生产部署**上线前检查**与**日常 Runbook**，可作为团队标准模板。

## 上线 Checklist

### 架构

- [ ] 架构选型文档已评审（单机/主从/哨兵/Cluster）
- [ ] 容量规划：内存、QPS、连接数有压测数据
- [ ] HA：Sentinel ≥3 或 Cluster 3主3从，跨 AZ 部署

### 配置

- [ ] `requirepass` + ACL 最小权限
- [ ] `bind` 限制内网，`protected-mode yes`
- [ ] `maxmemory` + 淘汰策略已设
- [ ] AOF/RDB 按 RPO 要求开启
- [ ] 危险命令 rename 或禁用
- [ ] `maxclients` 与应用连接池联动

### 可观测

- [ ] redis_exporter + Prometheus 抓取
- [ ] Grafana Dashboard 就绪
- [ ] P0/P1 告警规则 + Runbook 链接
- [ ] 慢日志开启并采集

### 备份与 DR

- [ ] 自动备份 cron + 异地存储
- [ ] 恢复演练 3 个月内有过成功记录

### 安全

- [ ] 无公网暴露
- [ ] TLS（若要求）
- [ ] 网络 ACL / Security Group

---

## 日常 Runbook

### 主库不可写

```bash
redis-cli INFO replication
redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster
# 检查 OOM、磁盘满、AOF 错误
```

### 内存告警

1. `INFO memory` → `used_memory_human`
2. `redis-cli --bigkeys` 抽样
3. 临时：扩容 / 提高 maxmemory / 清理过期 key
4. 长期：架构拆分、本地缓存

### 复制中断

1. 检查网络、密码、主库 load
2. 从库 `REPLICAOF NO ONE` 仅应急，需 Sentinel 协调

### 紧急回滚

1. 停止写入（应用开关）
2. 从最近 RDB 恢复新实例
3. DNS/Sentinel 指向恢复实例
4. 验证 DBSIZE 与抽样 key

---

## 文档维护

- Runbook 随每次故障复盘更新
- Checklist 版本号纳入变更工单
- 新人 onboarding 第一周完成 Redis 架构 walkthrough

---

**Redis SRE 系列 20 篇**至此完结，覆盖部署、HA、持久化、安全、K8s、监控、备份、性能、治理、升级、容灾与演练。建议按编号顺序阅读，并结合实际环境搭建 staging 集群动手实践。
