---
title: 阿里云 ECS 生产部署与运维
date: 2026-08-26 09:30:00
tags:
  - 阿里云
  - ECS
categories:
  - 阿里云资源 SRE
---

ECS 是阿里云最基础的计算资源，SRE 需规范规格、镜像、磁盘与高可用。

## 规格选型

| 场景 | 规格族 |
|------|--------|
| 通用 Web | g8y（倚天）/ g7 |
| 计算密集 | c7 |
| 内存密集 | r7 |
| GPU | gn7 / gn6v |

```
4C8G 起步 Web
8C16G 中等应用
按 CloudMonitor CPU/内存 P95 扩缩
```

## 系统盘与数据盘

```
系统盘：ESSD PL0/PL1，≥ 40GB
数据盘：ESSD PL1/PL2，独立挂载 /data
禁止业务数据仅放系统盘
```

```bash
# 数据盘格式化挂载
mkfs.ext4 /dev/vdb
mkdir /data
echo '/dev/vdb /data ext4 defaults 0 0' >> /etc/fstab
```

## 镜像与初始化

- 使用**自定义镜像**或 Alibaba Cloud Linux 3
- 用户数据 cloud-init 统一初始化：

```bash
#!/bin/bash
yum install -y node_exporter
systemctl enable --now node_exporter
```

## 高可用

```
SLB/ALB → 多 ECS（跨 AZ）→ 无单点
配合 ESS 弹性伸缩（最小 2 跨 AZ）
```

## 运维要点

| 项 | 实践 |
|----|------|
| 密钥对 | 禁止密码登录，RAM 跳板 |
| 安全组 | 最小端口 |
| 补丁 | OOS 批量打补丁 |
| 释放保护 | 生产 ECS 开启 |
| 快照 | 云盘自动快照策略 |

## 常见问题

| 问题 | 排查 |
|------|------|
| 磁盘满 | df -h，扩容云盘（在线） |
| CPU 高 | top，是否需升规格或 HPA |
| 网络不通 | 安全组、NACL、路由表 |

ECS 是**自建中间件载体**，托管服务能替代则优先 RDS/Redis/ACK。
