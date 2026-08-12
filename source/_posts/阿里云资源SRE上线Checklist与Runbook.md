---
title: 阿里云资源 SRE 上线 Checklist 与 Runbook
date: 2026-08-26 13:45:00
tags:
  - 阿里云
  - SRE
  - Runbook
categories:
  - 阿里云资源 SRE
---

## 上线 Checklist

### 账号与治理

- [ ] 生产独立账号/资源组
- [ ] 标签 env/app/team/owner/cost-center 必填
- [ ] RAM MFA 强制，无主账号 AK
- [ ] ActionTrail 开启

### 网络

- [ ] VPC 私网部署，无 DB 公网
- [ ] 安全组最小权限
- [ ] 多 AZ 子网
- [ ] NAT 多 AZ

### 计算与容器

- [ ] ECS/ACK 跨 AZ
- [ ] ESS min ≥ 2
- [ ] 镜像/节点池版本文档化

### 数据与存储

- [ ] RDS 高可用 + 自动备份 + 跨地域（核心）
- [ ] Redis 高可用 + 内存告警
- [ ] OSS 生命周期 + 版本控制/回收站
- [ ] 云盘快照策略

### 入口与 DNS

- [ ] SLB/ALB 健康检查 + HTTPS
- [ ] CDN/DNS TTL 合理
- [ ] 证书过期告警

### 可观测

- [ ] CloudMonitor 告警模板
- [ ] SLS 日志采集
- [ ] P0/P1 Runbook 链接

### 成本与安全

- [ ] 预算告警
- [ ] 闲置资源巡检
- [ ] 云安全中心基线

---

## 日常 Runbook

### RDS 连接失败（P0）

```
控制台监控 → 主备状态 → 白名单 → 连接数 → 切换事件
```

### SLB 全后端不可用（P0）

```
健康检查 → ECS/ACK Pod → 安全组 → 最近发布 → 回滚
```

### ECS 磁盘满

```
云监控 → SSH 清理 → 在线扩容云盘
```

### 费用异常（P2）

```
费用中心明细 → 标签筛选 → 释放闲置
```

### Region/AZ 故障

```
官方公告 → 跨 AZ 是否自动恢复 → DR Region Runbook → DNS 切流
```

---

**阿里云资源 SRE 系列 20 篇**完结，涵盖账号、ECS、VPC、SLB、RDS、Redis、OSS、ACK、监控、RAM、成本、备份、CDN、消息队列、容灾、弹性与演练。建议配合 **MySQL/Redis/Kafka/Jenkins SRE** 及自建中间件系列对照阅读。
