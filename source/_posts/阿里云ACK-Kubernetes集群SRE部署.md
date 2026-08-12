---
title: 阿里云 ACK Kubernetes 集群 SRE 部署
date: 2026-08-26 11:00:00
tags:
  - 阿里云
  - ACK
  - Kubernetes
categories:
  - 阿里云资源 SRE
---

ACK 是阿里云托管 K8s，SRE 需规范集群版本、节点池、网络与插件。

## 集群类型

| 类型 | 适用 |
|------|------|
| ACK 托管版 | 生产推荐，Master 托管 |
| ACK Serverless | 弹性、Job 类 |
| 专有版 | 需控 Master（少见） |

## 生产配置

```
K8s 版本：1.28+ LTS
网络：Terway（ENI）或 Flannel
Service CIDR：172.21.0.0/20
Pod CIDR：与 VPC 规划不冲突
```

## 节点池

```yaml
# 多节点池示例
apiPool:     3 × ecs.g7.2xlarge（跨 AZ）
gpuPool:     按需弹性（GPU 实例）
spotPool:    可中断任务（可选）
```

```
系统盘：ESSD 120GB
数据盘：容器镜像单独盘
kubelet 预留：system-reserved
```

## 必装组件

| 组件 | 用途 |
|------|------|
| ARMS Prometheus | 监控 |
| logtail-ds | 日志 |
| ALB Ingress | 七层入口 |
| ack-node-problem-detector | 节点故障 |
| cluster-autoscaler | 弹性 |

## RBAC 与 RAM

```
RRSA（Pod 关联 RAM 角色）
  → Pod 访问 OSS/SLS 无需 AK 硬编码
```

## 升级策略

1. 先升级 Master（托管自动）
2. 节点池滚动升级
3. staging 集群先行验证

## Checklist

- [ ] 3 AZ 节点分布
- [ ] API Server 公网访问关闭或 IP 白名单
- [ ] Secret 加密（KMS）
- [ ] NetworkPolicy 默认 deny（可选）
- [ ] etcd 备份（托管自动）

ACK 上跑 **Flink/Jenkins/OpenSearch** 等见各产品 SRE 系列。
