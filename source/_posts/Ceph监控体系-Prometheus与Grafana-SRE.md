---
title: Ceph 监控体系：Prometheus 与 Grafana
date: 2026-08-31 10:00:00
tags:
  - Ceph
  - SRE
  - Prometheus
categories:
  - Ceph SRE
---

生产 Ceph **必须** 有 Prometheus + 告警，不能仅靠 `ceph -s`。

## 启用与 scrape

```bash
ceph mgr module enable prometheus
ceph mgr services | grep prometheus
# http://<mgr>:9283/
```

```yaml
scrape_configs:
  - job_name: ceph
    honor_labels: true
    static_configs:
      - targets: ['ceph-mgr1:9283', 'ceph-mgr2:9283']
```

## 核心 SLI 指标

| 指标 | SLI |
|------|-----|
| ceph_health_status | 集群健康 |
| ceph_osd_up | OSD 存活 |
| ceph_osd_utilization | 容量 |
| ceph_pg_active | PG 状态 |
| ceph_pool_rd_bytes / wr_bytes | 吞吐 |
| ceph_osd_apply_latency_ms | 写延迟 |

## Grafana

- Dashboard：**Ceph - Cluster**（社区 2842 等）
- 面板分层：Cluster → OSD → Pool → RGW

## 日志

```bash
ceph log last 50
journalctl -u ceph-osd@12 -f
/var/log/ceph/ceph-audit.log
```

接入 Loki/ELK，保留 **audit** 合规。

## Recording rules 示例

```yaml
- record: ceph:osd_utilization:max
  expr: max(ceph_osd_utilization)
```

## 反模式

- 无 OSD full 告警
- 只监控 MGR 不监控节点 disk/网络
- recovering 时无容量监控

监控上线门禁：**HEALTH_ERR → P0 5 分钟内**。
