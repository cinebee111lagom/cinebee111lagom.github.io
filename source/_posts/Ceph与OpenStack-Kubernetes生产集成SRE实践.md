---
title: Ceph 与 OpenStack、Kubernetes 生产集成 SRE 实践
date: 2026-08-31 13:45:00
tags:
  - Ceph
  - SRE
  - 集成
categories:
  - Ceph SRE
---

生产环境 Ceph 常同时服务 **OpenStack 与 K8s**，SRE 需统一治理 pool 与故障域。

## 集成架构

```
                    Ceph Cluster
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   Cinder/Glance    RBD CSI          RGW (S3)
   (OpenStack)      (Kubernetes)     (备份/应用)
        │                │
   volumes pool    kubernetes pool
```

## Pool 与 client 隔离

| 消费者 | Pool | Cephx user |
|--------|------|------------|
| Cinder | volumes | client.cinder |
| Glance | images | client.glance |
| K8s CSI | kubernetes | client.kubernetes |
| RGW | rgw | RGW users |

## 故障影响分析

| 故障 | OpenStack | K8s |
|------|-----------|-----|
| 单 OSD | 无感 | 无感 |
| MON quorum 丢 | API 阻塞 | PVC 挂 |
| cluster full | 创建卷失败 | Pod Pending |
| CSI down | - | 新 PVC 失败 |

## 联合 Runbook

```
1. ceph -s 确认存储层
2. 若 Ceph OK → 查 Cinder/CSI
3. 若 Ceph ERR → 存储 SRE 主导
4. 业务方沟通 IO 影响
```

## 容量分摊

按 pool 报表：**OpenStack 租户 vs K8s namespace**，公平配额。

## 变更协调

- Ceph 升级窗口通知 IaaS/PaaS
- pg_num 变更低峰
- 新 pool 先 staging 双栈验证

## 反模式

- Cinder 与 CSI 共 client.admin
- 无跨平台变更通知
- OpenStack 与 K8s 抢同一 pool 无 quota

---

**Ceph SRE 系列 20 篇**完结，覆盖生产部署、监控、灾备、性能与集成。建议与 **Ceph 新手入门** 系列对照阅读。
