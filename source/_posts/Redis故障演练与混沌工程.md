---
title: Redis 故障演练与混沌工程
date: 2026-08-13 18:30:00
tags:
  - Redis
  - 混沌工程
categories:
  - Redis SRE
---

没演练过的 failover，真故障时一定翻车。

## 演练场景

| 场景 | 注入方式 | 预期 |
|------|----------|------|
| 主库进程 kill | `kill -9 redis-server` | Sentinel 60s 内 failover |
| 主库网络隔离 | iptables DROP | 客户端自动切新主 |
| 从库全挂 | 停所有 replica | 主库可写，无读扩展 |
| 内存打满 | 灌数据至 maxmemory | 淘汰或 OOM 告警 |
| 慢命令阻塞 | DEBUG SLEEP | 延迟告警触发 |
| AZ 故障 | 关整 AZ 节点 | 跨 AZ 拓扑恢复 |

## 混沌工具

- **Chaos Mesh**（K8s）：Pod kill、网络延迟
- **tc** / **iptables**：网络故障
- 脚本定时 kill + 监控验证

## 演练流程

1. 变更窗口公告（或 staging 环境）
2. 注入故障 → 观察告警
3. 记录 RTO、数据丢失量
4. 复盘改进 runbook
5. 输出演练报告

## 成功标准

- P0 告警 2 分钟内触达值班
- 自动 failover 无需人工（或人工 5 步内完成）
- 业务错误率 < 0.1% 且 5 分钟内恢复

## 频率

- Sentinel failover：每季度
- 全链路 DR：每半年
- 新架构上线前：必须演练

混沌工程把**未知**变成**已知**，是 SRE 成熟度的试金石。
