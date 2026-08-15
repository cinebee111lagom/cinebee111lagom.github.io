---
title: etcd 底层：数据目录文件布局
date: 2026-09-12 09:20:00
tags:
  - etcd
  - 存储
categories:
  - etcd v3.7 底层细节
---

长期存在的关键文件（`./member/...`）：

| 路径 | 作用 |
|------|------|
| `snap/db` | bbolt：已 apply 的数据、成员/鉴权元数据；含 `consistent_index` |
| `snap/*.snap` | 遗留 v2 快照类文件；v3 内容已冗余，定期保留最近若干 |
| `snap/*.snap.db` | 落后副本从 leader 拉取的完整 bbolt 快照 |
| `wal/*.wal` | Raft WAL：近期共识日志/快照/CRC；默认保留最近若干段 |
| `wal/0.tmp` 等 | 预分配下一段 WAL，降低“盘满写不进”的风险 |

临时文件：`*.snap.broken`、下载中的 `tmp*`、defrag 用的 `db.tmp.*`。异常杀进程可能留下 GB 级临时文件，需巡检磁盘。

> 延伸阅读：[Persistent storage files](https://etcd.io/docs/v3.7/learning/persistent-storage-files/)

