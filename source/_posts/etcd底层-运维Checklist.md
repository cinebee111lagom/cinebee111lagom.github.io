---
title: etcd 底层：运维 Checklist（实现视角）
date: 2026-09-12 09:24:00
tags:
  - etcd
  - Checklist
categories:
  - etcd v3.7 底层细节
---

## 存储与历史

- [ ] 自动 compaction 已配且有效
- [ ] 定期 defrag（低峰）
- [ ] db 大小与 quota 告警
- [ ] 巡检残留 `tmp*` / 过大 `snap.db`

## 共识与 IO

- [ ] 专用 SSD；监控 fsync
- [ ] heartbeat/election 与 RTT 匹配且全员一致
- [ ] peer 网络优先于海量 client

## 正确性

- [ ] 默认线性读的延迟已评估；热路径才用 serializable
- [ ] Watch 续订带 revision；压缩窗口够用
- [ ] 锁/选主理解 lease 过期语义

## 变更

- [ ] 成员变更优先 Learner 路径
- [ ] 备份用 etcdctl snapshot 并演练 restore

> 延伸阅读：[Tuning](https://etcd.io/docs/v3.7/tuning/)

