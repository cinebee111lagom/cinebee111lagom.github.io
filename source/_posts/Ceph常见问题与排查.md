---
title: Ceph 常见问题与排查
date: 2026-08-30 13:15:00
tags:
  - Ceph
  - 排查
  - 入门
categories:
  - Ceph 新手入门
---

Ceph 告警多时别慌，按 **health detail → PG → OSD 日志** 顺序查。

## cluster full / nearfull

```bash
ceph -s
ceph osd df tree
```

| 状态 | 动作 |
|------|------|
| nearfull (85%) | 扩容 OSD 或删数据 |
| backfillfull | 暂停 backfill，紧急扩容 |
| full | **只读**，立即扩容 |

```bash
ceph osd set-nearfull-ratio 0.85
ceph osd set-full-ratio 0.95
```

## OSD down

```bash
ceph osd tree | grep down
systemctl status ceph-osd@5   # 或 ceph orch ps
journalctl -u ceph-osd@5 -f
```

常见：磁盘故障、内存不足、网络中断。

## PG stuck

```bash
ceph pg dump_stuck inactive
ceph pg <pgid> query
```

可能：MON/OSD 版本不一致、CRUSH 规则错误、OSD 过少。

## slow ops

```bash
ceph daemon osd.0 dump_ops_in_flight
ceph tell osd.0 bench
```

查磁盘 SMART、网络延迟、负载。

## MON 无 quorum

```bash
ceph mon stat
# 保证奇数 MON，至少 majority 存活
# 检查 clock skew、防火墙 6789
```

## 恢复期间 WARN

`recovering`、`backfilling` 通常是 **正常**，等 `active+clean`。

勿频繁 restart OSD。

## 排查流程

```
health ERR/WARN
  → health detail
  → pg stat / dump_stuck
  → osd tree / df
  → daemon 日志
```

## 反模式

- full 状态下删 pool 当扩容
- 同时重启所有 MON
- 无备份改 CRUSH

收藏本文作 **Ceph 值班速查**。
