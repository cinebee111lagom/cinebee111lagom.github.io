---
title: ceph 命令行基础入门
date: 2026-08-30 11:15:00
tags:
  - Ceph
  - CLI
  - 入门
categories:
  - Ceph 新手入门
---

`ceph` CLI 是日常运维第一工具，与 Dashboard 能力互补。

## 集群状态

```bash
ceph -s                    # 摘要（最常用）
ceph status                # 同 -s
ceph health detail         # 告警详情
ceph versions              # 各组件版本
ceph df                    # 容量
ceph df detail             # 按 pool 容量
```

## OSD / MON

```bash
ceph osd stat
ceph osd tree              # 拓扑树
ceph osd df tree           # 每 OSD 使用率
ceph mon stat
ceph mon dump
```

## Pool / PG

```bash
ceph osd pool ls detail
ceph pg stat
ceph pg dump_stuck          # 卡住 PG
ceph osd pool get rbd_pool all
```

## 服务管理（cephadm）

```bash
ceph orch ps               # 所有 daemon
ceph orch ls               # 服务 spec
ceph orch host ls          # 主机
ceph orch device ls        # 磁盘
```

## 日志与调试

```bash
ceph log last 20
ceph daemon osd.0 config show | head
```

## 危险命令（慎用）

```bash
ceph osd out osd.1         # 标记 OSD 出局
ceph osd crush remove ...  # 改 CRUSH
ceph osd pool delete ...   # 删 pool
```

生产需 **变更单 + 备份**。

## 输出格式

```bash
ceph -s -f json
ceph -s -f json-pretty
```

脚本化用 JSON。

## 反模式

- 不看 `health detail` 就 reboot 节点
- 不熟命令直接 `--yes-i-really-mean-it`
- 无文档记录变更

下一篇：**健康检查与状态解读**。
