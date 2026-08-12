---
title: cephadm 集群部署入门
date: 2026-08-30 10:00:00
tags:
  - Ceph
  - cephadm
  - 入门
categories:
  - Ceph 新手入门
---

**cephadm** 用容器部署 Ceph，是当前官方推荐方式。

## Bootstrap（第一台）

```bash
cephadm bootstrap --mon-ip 10.0.0.11 --cluster-network 10.0.1.0/24

# 输出示例
# Dashboard URL: https://ceph-node1:8443/
# User: admin
# Password: xxxx
```

- `--mon-ip`：MON 对外 IP
- `--cluster-network`：OSD 复制网络（可与 public 相同，生产建议分离）

## 添加节点

```bash
# 复制 SSH key
ssh-copy-id -f root@ceph-node2

# 添加主机
ceph orch host add ceph-node2 10.0.0.12
ceph orch host add ceph-node3 10.0.0.13

ceph orch host ls
```

## 添加 OSD

```bash
# 自动扫描可用磁盘
ceph orch device ls

# 批量添加（所有可用设备）
ceph orch apply osd --all-available-devices

# 或指定设备
ceph orch daemon add osd ceph-node2:/dev/sdb
```

## 验证集群

```bash
ceph -s
ceph osd stat
ceph df
ceph orch ps
```

期望：`health: HEALTH_OK`（新建集群可能 WARN，OSD up 后变 OK）。

## 启用 MGR Dashboard

bootstrap 已启用，浏览器访问 `https://<node>:8443`。

## 常用 orch 命令

```bash
ceph orch ls              # 服务列表
ceph orch daemon ls       # 守护进程
ceph orch restart osd     # 重启 OSD（维护）
```

## 反模式

- bootstrap 后不 add 节点就写满单节点
- 系统盘误当 OSD 盘
- 不记录 dashboard 初始密码

下一篇：**Pool 创建与管理**。
