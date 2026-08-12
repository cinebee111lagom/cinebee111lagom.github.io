---
title: 阿里云生产上线 Checklist 与 Runbook
date: 2026-08-25 13:45:00
tags:
  - 阿里云
  - SRE
  - Runbook
categories:
  - 阿里云资源 SRE
---

本文汇总阿里云生产**上线前检查**与**常见故障 Runbook**，作为系列收官篇。

## 上线 Checklist

### 账号与治理

- [ ] RAM 角色最小权限，无 AK 硬编码
- [ ] 资源组 + Tag（project/env/owner/cost-center）
- [ ] ActionTrail 开启

### 网络

- [ ] VPC 私网，无公网 RDS/Redis
- [ ] 安全组最小放通
- [ ] SLB/ALB 健康检查配置
- [ ] NAT 仅出口必需

### 计算与容器

- [ ] ECS 多 AZ 或 ACK 多节点池
- [ ] ESS min ≥ 2
- [ ] 镜像/版本固定，UserData 幂等

### 数据

- [ ] RDS 高可用 + 自动备份
- [ ] 连接池、只读分离（如需要）
- [ ] OSS 私有 + 生命周期

### 可观测

- [ ] 云监控/ARMS 指标接入
- [ ] 日志 SLS 采集
- [ ] 告警规则 + 值班路由
- [ ] 大盘（核心 SLI）

### 安全

- [ ] WAF / DDoS（公网 Web）
- [ ] KMS 加密
- [ ] 堡垒机运维

### 容灾与成本

- [ ] 备份策略 + 恢复演练记录
- [ ] 预算告警
- [ ] 跨 AZ 无单点

## Runbook：RDS 主备切换后应用连不上

```
1. 确认新主 endpoint（控制台）
2. 检查应用连接串是否用域名（非 IP）
3. 连接池 flush / 应用滚动重启
4. 验证只读延迟、binlog 同步
5. 复盘：连接串、DNS TTL、监控
```

## Runbook：SLB 5xx 突增

```
1. ARMS/SLB 看后端健康数
2. 不健康 → SSH/日志查 ECS/OSS
3. 健康但 5xx → 应用日志、RDS 慢查
4. 容量 → ESS 扩容
5. 回滚最近发布
```

## Runbook：OSS 访问 403

```
1. Bucket ACL / Policy
2. RAM 角色权限
3. STS 过期
4. CDN 回源鉴权
5. 跨 Region CRR 延迟
```

## Runbook：ACK Pod Pending

```
1. describe pod events
2. 资源不足 → 扩容节点池
3. PVC 未绑定 → 存储类/配额
4. 镜像拉取失败 → ACR 权限
5. taint/toleration 不匹配
```

## Runbook：成本异常飙升

```
1. 费用中心按 Tag 排序
2. 按量 ECS/RDS 新建？泄漏 EIP？
3. OSS 流量 / CDN 带宽
4. 临时升配未回退
5. 冻结新建 + 回收闲置
```

## 值班交接模板

```
- 当前告警（P0/P1）
- 进行中变更
- 大促/演练窗口
- 已知风险（DTS 延迟、磁盘 80%）
- 联系人（DBA/网络/安全）
```

## 系列回顾

| 主题 | 文章 |
|------|------|
| 入门 | 职责与目标、架构选型 |
| 治理 | RAM、Tag、IaC |
| 核心产品 | ECS、VPC、SLB、RDS、OSS、ACK |
| 可观测 | 监控、告警、值班 |
| 弹性成本 | ESS、FinOps |
| 安全容灾 | 安全配置、备份、多 AZ/Region |
| 工程化 | CDN/DNS、混沌、Checklist |

**SRE 在阿里云上的目标：稳定、可观测、可恢复、成本可控**。
