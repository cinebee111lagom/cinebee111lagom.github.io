---
title: MinIO 纠删码与节点故障恢复 Runbook
date: 2026-09-02 12:30:00
tags:
  - MinIO
  - SRE
  - 故障
categories:
  - MinIO SRE
---

EC 允许磁盘/节点故障，但 **恢复窗口内再次故障** 可能丢数据。

## 单盘故障

```
1. 告警 minio_cluster_drive_offline_total
2. 确认 SMART/硬件
3. 换盘，同 path 或新 path
4. minio 自动 heal
5. mc admin heal alias --recursive bucket/  # 可选加速
6. 观察 mc admin info until heal complete
```

## 单节点故障

```
1. LB 自动摘除
2. 业务应持续（EC）
3. 修节点/换机
4. 重装 MinIO，加入相同 erasure set 拓扑
5. heal 完成前避免再丢节点
```

## 多节点/多盘（危险）

```
评估是否只读
紧急扩容或 mc admin decommission（若支持）
联系 MinIO 支持/社区
从 DR 复制拉数据
```

## heal 监控

```bash
mc admin heal alias
mc admin heal alias --recursive --json | head
```

## 禁止

- 同时下线 > 可容忍故障数
- 满盘状态 heal
- 未 heal 完成再升级

## CMDB

节点、盘位、WWN、加入日期、故障次数。
