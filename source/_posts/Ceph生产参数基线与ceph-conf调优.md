---
title: Ceph 生产参数基线与 ceph.conf 调优
date: 2026-08-31 09:45:00
tags:
  - Ceph
  - SRE
  - 基线
categories:
  - Ceph SRE
---

cephadm 管理配置于 **MGR config database**，生产需 **基线文档 + 变更审计**。

## 常用 runtime 配置

```bash
# 查看
ceph config dump
ceph config get osd osd_mclock_max_capacity_iops_ssd

# 设置（示例：nearfull 阈值）
ceph osd set-nearfull-ratio 0.80
ceph osd set-backfillfull-ratio 0.85
ceph osd set-full-ratio 0.90
```

## 生产基线建议

| 参数 | 建议 |
|------|------|
| mon_osd_full_ratio | 0.90~0.95 |
| mon_osd_nearfull_ratio | 0.80~0.85 |
| osd_pool_default_size | 3 |
| osd_pool_default_min_size | 2 |
| ms_bind_ipv4 | true |

## mClock（Reef+ 默认调度）

SSD 集群可设 QoS 优先级，避免 recovery 打满业务 IO。

```bash
ceph config set osd osd_mclock_profile high_client_ops
```

## BlueStore 缓存

大内存 OSD 节点：

```bash
ceph config set osd bluestore_cache_size_ssd 4294967296  # 4Gi
```

## 变更流程

1. staging 集群验证
2. `ceph config set` 或 orch 更新
3. 观察 24h：latency、recovery、WARN
4. 文档化

## 反模式

- full_ratio=0.99 导致突然只读
- 全集群同时改 osd 参数无分批
- 不备份 `ceph config dump`

`ceph.conf` 本地文件由 cephadm 生成，**勿手工改而不 reconfigure**。
