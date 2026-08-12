---
title: Ceph 生产安全配置与网络隔离
date: 2026-08-31 11:45:00
tags:
  - Ceph
  - SRE
  - 安全
categories:
  - Ceph SRE
---

Ceph 持有 **全公司数据**，cepxh 与网络隔离是底线。

## cephx

```bash
ceph auth ls
# 每客户端最小权限
ceph auth get-or-create client.k8s mon 'profile rbd' osd 'profile rbd pool=kubernetes'
```

**禁止** client.admin 给 K8s/OpenStack。

## 网络隔离

| 平面 | ACL |
|------|-----|
| Public | 仅 K8s/OpenStack/堡垒机 |
| Cluster | 仅 OSD 节点互访 |
| MON | 6789 限管理网 |
| RGW | 443 对外，8080 内网 |

```bash
# MSGR2 加密（可选）
ceph config set global ms_cluster_mode secure
ceph config set global ms_service_mode secure
```

## RGW 安全

- HTTPS 必须
- IAM 风格用户、bucket policy
- 禁用 public bucket（默认）

## Dashboard

- 强密码 / SSO
- 不暴露公网
- 只读账号给开发

## 审计

```bash
ceph config set global auth_allow_insecure_global_id_reclaim false
# audit log → SIEM
```

## 反模式

- 公网暴露 OSD 端口
- keyring 进 Git 明文
- 共享 admin key 给所有 CSI

安全配置进 **上线 Checklist**（第 19 篇）。
