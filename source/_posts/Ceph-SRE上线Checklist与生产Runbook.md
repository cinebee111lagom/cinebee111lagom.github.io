---
title: Ceph SRE 上线 Checklist 与生产 Runbook
date: 2026-08-31 13:30:00
tags:
  - Ceph
  - SRE
  - Runbook
categories:
  - Ceph SRE
---

## 上线 Checklist

### 架构

- [ ] MON 3+/5，跨 failure domain
- [ ] MGR 2，Dashboard 可用
- [ ] Public/Cluster 网络分离
- [ ] CRUSH failure domain = host/rack

### 存储

- [ ] Pool 规划文档化，pg_num 合理
- [ ] 副本 size=3 min_size=2
- [ ] nearfull/full ratio 已设

### 安全

- [ ] cephx 最小 client
- [ ] Dashboard/RGW TLS
- [ ] 防火墙规则生效

### 监控

- [ ] Prometheus scrape MGR
- [ ] Grafana Dashboard
- [ ] P0/P1 告警 + Runbook

### 备份

- [ ] crush/config 备份
- [ ] 核心 RBD snap/export 策略
- [ ] 3 个月内 restore 演练

### 集成

- [ ] K8s CSI / OpenStack Cinder 验收
- [ ] 性能 baseline 存档

---

## 日常 Runbook

| 频率 | 动作 |
|------|------|
| 每日 | health、nearfull、OSD down |
| 每周 | pool 用量、recovery 状态 |
| 每月 | SMART 抽检、auth 审计 |
| 每季 | 升级 staging、OSD 演练 |

## 应急

| 事件 | 动作 |
|------|------|
| HEALTH_ERR | detail → PG/OSD Runbook |
| full | 紧急扩容/清 RGW |
| 多 OSD down | 停业务写、硬件排查 |
| 慢 IO | perf bench → 磁盘/网络 |

## 反模式

- Checklist 未执行即接生产 PVC
- 无 on-call 存储工程师

配合 **Ceph 新手入门** 系列使用。
