---
title: Ceph 监控与 Prometheus 入门
date: 2026-08-30 12:30:00
tags:
  - Ceph
  - Prometheus
  - 入门
categories:
  - Ceph 新手入门
---

Ceph MGR **内置 Prometheus 模块**，开箱导出丰富指标。

## 启用模块

```bash
ceph mgr module enable prometheus
ceph mgr services
# 输出 prometheus 地址，如 http://ceph-node1:9283/
```

## Prometheus scrape

```yaml
scrape_configs:
  - job_name: ceph
    honor_labels: true
    static_configs:
      - targets:
          - ceph-node1:9283
```

## 关键指标

| 指标 | 含义 |
|------|------|
| ceph_health_status | 0=OK, 1=WARN, 2=ERR |
| ceph_osd_up | OSD 是否 up |
| ceph_osd_utilization | OSD 使用率 |
| ceph_pg_active | PG 状态分布 |
| ceph_pool_stored | Pool 已用容量 |

## Grafana Dashboard

- 官方/社区：**Ceph Cluster** dashboard（Ceph 文档推荐 ID）
- 面板：OSD 使用率、IOPS、延迟、PG 状态

## Dashboard（MGR）

```bash
ceph mgr module enable dashboard
ceph dashboard ac-user-show admin
# 或 bootstrap 时已启用
```

Web UI 看 **Cluster / OSD / Pool** 直观状态。

## 告警起步

```yaml
- alert: CephHealthError
  expr: ceph_health_status == 2
  for: 5m

- alert: CephOSDDown
  expr: ceph_osd_up == 0
  for: 5m

- alert: CephOSDFull
  expr: ceph_osd_utilization > 0.85
  for: 15m
```

## 反模式

- 无监控靠 `ceph -s` 人工看
- 不告警 OSD near full
- Prometheus 无法 scrape MGR

下一篇：**快照与克隆**。
