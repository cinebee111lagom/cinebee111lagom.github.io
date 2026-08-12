---
title: MySQL 故障演练与混沌工程
date: 2026-08-14 13:30:00
tags:
  - MySQL
  - 混沌工程
categories:
  - MySQL SRE
---

## 演练场景

| 场景 | 注入 | 预期 |
|------|------|------|
| 主库 kill | systemctl kill mysqld | 60s 内 failover |
| 主库网络隔离 | iptables | Proxy 切从库 |
| 从库全挂 | 停所有 replica | 主库可写，无读扩展 |
| 磁盘满 | dd 填盘 | 告警 + 只读保护 |
| 大事务 | 批量 UPDATE | 复制延迟告警 |
| AZ 故障 | 关 AZ 节点 | MGR/Orchestrator 恢复 |

## 工具

- Chaos Mesh Pod kill / 网络延迟
- 自定义脚本 + 监控验证

## 流程

1. staging 或隔离生产子集
2. 注入 → 观察告警与自动切换
3. 记录 RTO、数据一致性
4. 复盘更新 runbook

## 成功标准

- P0 告警 2 分钟内触达
- 自动 failover 或 runbook 5 步内完成
- 业务错误率 < 0.1%

## 频率

- Failover：每季度
- 全量 DR：每半年
- 新 HA 架构上线前：必演练

混沌演练把**纸面 HA**变成**真实 HA**。
