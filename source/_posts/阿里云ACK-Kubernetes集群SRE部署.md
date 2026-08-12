---
title: 阿里云 ACK Kubernetes 集群 SRE 部署
date: 2026-08-25 12:00:00
tags:
  - 阿里云
  - ACK
  - Kubernetes
categories:
  - 阿里云资源 SRE
---

**ACK（容器服务 Kubernetes）** 是阿里云云原生生产标准，推荐托管版 Master。

## 集群选型

| 类型 | 说明 |
|------|------|
| ACK 托管版 | Master 阿里云运维（推荐） |
| ACK 专有版 | 自管 Master |
| ACK Serverless | 无节点 Serverless |

## 创建要点

```
Region：cn-hangzhou
网络：Terway（ENI 模式，性能优）或 Flannel
Worker：多 AZ 节点池
规格：ecs.g8i.xlarge 起步
数量：每 AZ ≥ 2
存储：ESSD 云盘
```

## 必装组件

| 组件 | 用途 |
|------|------|
| ARMS Prometheus | 监控 |
| Logtail | 日志 SLS |
| ALB Ingress | 七层入口 |
| GPU Operator | GPU 节点（可选） |
| ack-node-problem-detector | 节点故障 |

## 节点池隔离

```
node-pool-system：系统组件
node-pool-app：业务 Pod
node-pool-gpu：GPU 训练（taint）
```

## RAM 角色

```
Worker RAM Role：OSS、ACR、SLB 权限
RRSA：Pod 级 OSS 访问（推荐替代 AK）
```

## 升级

```
控制台：Master 自动升级
节点池：滚动升级，先扩容新节点再排水旧节点
```

## Checklist

- [ ] 托管 Master + 多 AZ Worker
- [ ] Terway + 固定 Pod IP（需规划 vSwitch）
- [ ] 非 default 命名空间跑生产
- [ ] ResourceQuota / LimitRange
- [ ] NetworkPolicy（可选零信任）

ACK SRE 与 **Kubernetes SRE** 系列（各中间件）配合阅读。
