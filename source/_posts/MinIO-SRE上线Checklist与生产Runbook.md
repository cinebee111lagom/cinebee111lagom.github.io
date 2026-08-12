---
title: MinIO SRE 上线 Checklist 与生产 Runbook
date: 2026-09-02 13:30:00
tags:
  - MinIO
  - SRE
  - Runbook
categories:
  - MinIO SRE
---

## 上线 Checklist

### 架构

- [ ] ≥4 节点分布式（或 Operator 4×4）
- [ ] LB + health check（live/ready）
- [ ] EC 布局 mc admin info 确认

### 安全

- [ ] TLS 全链路
- [ ] root 仅 break-glass
- [ ] 租户 svcacct + Policy
- [ ] public bucket 默认拒绝

### 容量

- [ ] quota/lifecycle 已配
- [ ] 预留 ≥15% 空间

### 监控

- [ ] Prometheus cluster/bucket/node
- [ ] Grafana Dashboard
- [ ] P0/P1 告警 + Runbook

### 灾备

- [ ] 桶复制或站点复制
- [ ] config/policy 备份
- [ ] DR 切换演练成功

### 文档

- [ ] endpoint、租户、bucket 清单 CMDB

---

## 日常 Runbook

| 频率 | 动作 |
|------|------|
| 每日 | 告警、容量 |
| 每周 | Top bucket、repl lag |
| 每月 | 密钥审计、证书有效期 |
| 每季 | 节点故障演练、升级 staging |

## 应急

| 事件 | 动作 |
|------|------|
| Cluster down | LB→节点→磁盘 |
| 容量满 | lifecycle/扩容 |
| 5xx 飙升 | warp/日志/网络 |
| 数据疑丢 | versioning/heal/DR |

## 反模式

- Checklist 未勾完接生产流量
- 无 on-call Runbook

配合 **MinIO 新手入门** 系列使用。
