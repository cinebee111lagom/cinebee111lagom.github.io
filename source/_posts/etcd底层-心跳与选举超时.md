---
title: etcd 底层：心跳间隔与选举超时
date: 2026-09-12 09:09:00
tags:
  - etcd
  - Raft
  - 调优
categories:
  - etcd v3.7 底层细节
---

Raft 靠两个时间参数保活与切主（默认：heartbeat **100ms**，election **1000ms**）：

| 参数 | 含义 | 建议 |
|------|------|------|
| Heartbeat Interval | Leader 通知仍在任 | ≈ RTT，约 0.5–1.5×RTT |
| Election Timeout | Follower 多久没心跳就竞选 | ≥ **10×RTT**，且全员一致 |

过小心跳：CPU/网络浪费；过大：故障发现慢。跨洋集群 election 上限可到 50s 量级，但要以实测 RTT 为准。

**磁盘慢 = 等效延迟**：fsync 慢会导致丢心跳、超时、切主——不只是网络问题。

> 延伸阅读：[Tuning](https://etcd.io/docs/v3.7/tuning/)

