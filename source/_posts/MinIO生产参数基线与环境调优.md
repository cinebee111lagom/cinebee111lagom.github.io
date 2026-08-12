---
title: MinIO 生产参数基线与环境调优
date: 2026-09-02 09:45:00
tags:
  - MinIO
  - SRE
  - 基线
categories:
  - MinIO SRE
---

生产 MinIO 通过 **环境变量 + mc admin config** 统一基线。

## 核心环境变量

```bash
MINIO_ROOT_USER=<from-vault>          # 勿用 admin 给应用
MINIO_ROOT_PASSWORD=<strong>
MINIO_PROMETHEUS_AUTH_TYPE=public     # 或 jwt，内网 scrape
MINIO_BROWSER=on                      # 生产可限制 Console 访问网段
MINIO_LOG_LEVEL=info
MINIO_AUDIT_WEBHOOK_ENABLE=on         # 审计到 SIEM
```

## mc admin config

```bash
mc admin config set alias api requests_max=10000
mc admin config set alias storage_class standard
mc admin service restart alias
```

## 系统调优（Linux）

```bash
# /etc/sysctl.d/minio.conf
fs.file-max = 1048576
net.core.somaxconn = 65535
net.ipv4.tcp_fin_timeout = 30

# 禁用磁盘调度器冲突（NVMe 通常 none）
# XFS 挂载 noatime
```

## 资源

| 规模 | CPU | 内存 | 网络 |
|------|-----|------|------|
| 小集群 | 8 核/节点 | 32 Gi | 10G |
| 中 | 16 核 | 64 Gi | 25G |

## 变更流程

1. staging 改 env/config
2. 滚动 restart 节点
3. `mc admin info` + 压测验证

## 反模式

- DEBUG 日志常开生产
- 无 file descriptor 限制规划
- root 密码进 systemd 明文

基线存 **Git + Ansible**，变更走工单。
