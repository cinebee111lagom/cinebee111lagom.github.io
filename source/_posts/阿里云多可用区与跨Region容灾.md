---
title: 阿里云多可用区与跨 Region 容灾
date: 2026-08-25 13:00:00
tags:
  - 阿里云
  - 容灾
  - 高可用
categories:
  - 阿里云资源 SRE
---

容灾分层：**单 AZ 故障 → 多 AZ → 跨 Region**，成本与 RTO 递增。

## 多 AZ（同城）

```
VPC 跨 2~3 个可用区
ECS：ESS 多 AZ 伸缩组
RDS：高可用版（主备跨 AZ）
SLB/ALB：多 AZ 挂载
Redis：集群版多 AZ
```

| 场景 | RTO |
|------|-----|
| 单 AZ 电力/网络 | 分钟级自动切换 |

## 跨 Region（异地）

```
主：cn-hangzhou
备：cn-shanghai 或 cn-beijing

数据：DTS 同步 / RDS 跨 Region 备份
存储：OSS CRR
流量：GTM 故障转移
```

| 场景 | RTO |
|------|-----|
| 整 Region 不可用 | 小时级（需人工/半自动） |

## 架构模式

| 模式 | RPO | RTO | 成本 |
|------|-----|-----|------|
| 冷备 | 小时~天 | 小时 | 低 |
| 温备 | 分钟~小时 | 30~60min | 中 |
| 热备（双活） | 秒~分钟 | 分钟 | 高 |

## 双活注意

```
- 数据冲突（写双活需 CRDT/分片）
- 会话粘性 vs 全局 Session
- 时钟与 ID 生成
```

## 切换流程

```
1. GTM 探测主 Region 故障
2. DNS 切到备 Region SLB
3. 确认 DTS 延迟可接受
4. 备库提升（如需要）
5. 业务验证 + 公告
```

## 演练

- 模拟主 AZ 下线（安全组隔离）
- 跨 Region 只读切换
- 全链路 Game Day 文档化

## Checklist

- [ ] 生产无单 AZ 单点
- [ ] RPO/RTO 书面定义
- [ ] 跨 Region 数据同步监控
- [ ] GTM 切换 Runbook
- [ ] 年度容灾演练

**容灾能力 = 架构 + 数据 + 流程 + 演练**。
