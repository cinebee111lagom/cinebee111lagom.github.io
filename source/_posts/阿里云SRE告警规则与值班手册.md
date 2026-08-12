---
title: 阿里云 SRE 告警规则与值班手册
date: 2026-08-25 11:15:00
tags:
  - 阿里云
  - SRE
  - 告警
categories:
  - 阿里云资源 SRE
---

云资源告警需分级、收敛，并与 Runbook 联动。

## 告警分级

| 级别 | 场景 | 响应 |
|------|------|------|
| P0 | RDS 主备切换失败、全站 5xx、ECS 批量宕机 | 5 分钟 |
| P1 | 单 AZ 资源异常、磁盘 >85%、SLB  unhealthy | 15 分钟 |
| P2 | CPU 持续高、成本异常、证书 30 天过期 | 1 小时 |
| P3 | 非核心资源、建议性优化 | 工作日 |

## 云监控规则示例

```
产品：RDS
规则：CPUUtilization >= 80%，持续 5 分钟
级别：P1
联系人组：dba-oncall

产品：SLB
规则：UnhealthyHostCount >= 1
级别：P0

产品：ECS
规则：StatusCheckFailed >= 1
级别：P0
```

## 值班速查

### ECS 不可达

```bash
# 控制台 VNC / 云助手
aliyun ecs DescribeInstances --InstanceId i-xxx
# 查 Status、SystemEvent（计划运维）
# 安全组、磁盘满、OOM
```

### RDS 故障

- 控制台查看实例状态、主备延迟
- 自动切换是否触发
- 连接数、慢 SQL
- 必要时手动主备切换

### SLB 5xx

- 后端 UnhealthyHostCount
- 后端 ECS 日志
- 证书是否过期
- WAF 是否误拦

### OSS 访问失败

- RAM 权限、Bucket Policy
- 跨 Region 复制延迟
- 欠费停服

### 欠费/配额

- 账户余额告警
- 云产品配额（ECS 台数、EIP）

## 告警收敛

- 同一资源 5 分钟内合并
- 维护窗口抑制
- 依赖拓扑（RDS 挂 → 抑制应用 CPU 告警）

## On-Call 原则

1. 先恢复（扩容、切换、回滚）
2. 控制台 + CLI + 日志三管齐下
3. 变更关联（是否刚发布）
4. 48h Postmortem

每季度 **告警 review**，删除噪音规则。
