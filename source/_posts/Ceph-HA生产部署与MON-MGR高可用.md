---
title: Ceph HA 生产部署与 MON、MGR 高可用
date: 2026-08-31 09:30:00
tags:
  - Ceph
  - SRE
  - HA
categories:
  - Ceph SRE
---

MON 丢 quorum 集群 **不可写**，MGR 宕机丢监控，生产必须 HA。

## MON 部署

```bash
# cephadm 通常 bootstrap 后自动 3 MON
ceph mon stat
ceph quorum_status --format json-pretty

# 扩展到 5 MON（大规模）
ceph orch apply mon --placement="5 label:mon"
```

| 规则 | 说明 |
|------|------|
| 奇数 | 3/5/7，容忍 (N-1)/2 故障 |
| 跨机架 | CRUSH 分散 MON |
| 低负载 | MON 不跑 OSD（大规模） |

## MGR HA

```bash
ceph mgr stat
ceph orch apply mgr --placement="2:ceph-node1;ceph-node2"
ceph mgr module ls
```

1 active + N standby，failover 秒级。

## 验收

```bash
# 模拟 MON 停 1 个（3 节点集群）
ceph orch daemon stop mon.ceph-node1
ceph -s   # 仍 HEALTH_OK，quorum 2/3
ceph orch daemon start mon.ceph-node1
```

## 时间同步

```bash
ceph time-sync-status
# MON clock skew → 立即修 NTP
timedatectl set-ntp true
```

## VIP / DNS

Client 连接 **多个 MON IP** 或 DNS 轮询，不用单 IP。

```
mon_host = 10.0.0.11,10.0.0.12,10.0.0.13
```

## 反模式

- 2 MON
- MON 与 OSD 同盘抢 IO 无隔离
- 防火墙阻断 6789 部分 MON

MON/MGR 故障演练 **季度** 一次。
