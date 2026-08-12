---
title: 阿里云 ECS 生产部署与运维
date: 2026-08-25 09:45:00
tags:
  - 阿里云
  - ECS
categories:
  - 阿里云资源 SRE
---

ECS 是阿里云最基础的计算资源，SRE 需规范镜像、规格、部署与巡检。

## 实例规格选型

| 系列 | 场景 |
|------|------|
| g8i | 通用均衡 |
| c8i | 计算密集 |
| r8i | 内存密集 |
| gn7/gn8 | GPU 训练/推理 |

生产推荐 **按量+预留实例券** 混合降本。

## 镜像与初始化

```bash
# 使用官方 Alibaba Cloud Linux 3 / Ubuntu 22.04
# 自定义镜像：cloud-init + 安全基线

#!/bin/bash
# user-data 示例
yum update -y
systemctl enable chronyd && systemctl start chronyd
# 安装监控 agent
wget -O install.sh http://update.aegis.aliyun.com/download/install.sh
bash install.sh
```

## 部署模式

| 模式 | 说明 |
|------|------|
| 单实例 | 仅 dev |
| 多实例 + SLB | 生产最小 HA |
| 弹性伸缩 ESS | 自动扩缩 |
| 部署集 | 物理分散，降 correlated failure |

## 云盘

| 类型 | 场景 |
|------|------|
| ESSD PL0/PL1 | 生产系统盘/数据盘 |
| 快照 | 每日自动快照策略 |
| 加密 | KMS 加密盘 |

## 运维命令

```bash
# 阿里云 CLI
aliyun ecs DescribeInstances --RegionId cn-hangzhou
aliyun ecs RebootInstance --InstanceId i-xxx

# 系统内
df -h
free -h
journalctl -xe
```

## 检查清单

- [ ] 密钥对/密码合规，禁止密码登录（SSH Key）
- [ ] 安全组最小放通
- [ ] 云监控 agent 安装
- [ ] 自动快照策略
- [ ] 非 root 跑应用
- [ ] 部署集（关键集群）

**ECS 不落单 AZ 单实例**（生产）。
