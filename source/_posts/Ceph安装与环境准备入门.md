---
title: Ceph 安装与环境准备入门
date: 2026-08-30 09:45:00
tags:
  - Ceph
  - 安装
  - 入门
categories:
  - Ceph 新手入门
---

现代 Ceph 推荐 **cephadm** 部署，传统 ceph-deploy/ansible 仍见于老集群。

## 环境要求

| 项 | 建议 |
|----|------|
| 节点数 | ≥ 3（MON+OSD 同机或分离） |
| OS | Ubuntu 22.04 / RHEL 8+ |
| 内存 | 每 OSD 节点 ≥ 16 Gi（NVMe 更多） |
| 磁盘 | 1 OS 盘 + 数据盘（裸盘或 LV） |
| 网络 | 10Gb+，双网卡更佳 |
| 时间 | NTP 同步（MON 敏感） |

## 主机名与解析

```bash
# /etc/hosts 或 DNS
10.0.0.11 ceph-node1
10.0.0.12 ceph-node2
10.0.0.13 ceph-node3
```

## 前置准备（每节点）

```bash
# 时间同步
timedatectl set-ntp true

# 防火墙（生产按策略开放 6789 MON、6800-7300 OSD 等）
# 学习环境可临时关闭便于排查

# 数据盘勿格式化，cephadm 会占用
lsblk
```

## 安装 cephadm（bootstrap 节点）

```bash
curl --silent --remote-name --location https://github.com/ceph/ceph/raw/quincy/src/cephadm/cephadm
chmod +x cephadm
./cephadm add-repo --release quincy
./cephadm install
```

版本与 [Ceph 发行版](https://docs.ceph.com/en/quincy/releases/) 对应，新手可用 **Quincy/Reef** 稳定版。

## SSH 免密

bootstrap 节点需 **root SSH 免密** 到其他节点（cephadm 编排用）。

```bash
ssh-copy-id root@ceph-node2
ssh-copy-id root@ceph-node3
```

## 验收 Checklist

- [ ] 三节点 hostname 唯一
- [ ] 时间差 < 50ms
- [ ] 数据盘无挂载、无文件系统
- [ ] cephadm 可执行

下一篇：**cephadm 集群部署**。
