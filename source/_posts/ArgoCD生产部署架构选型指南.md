---
title: Argo CD 生产部署架构选型指南
date: 2026-08-27 09:15:00
tags:
  - ArgoCD
  - SRE
  - 架构
categories:
  - ArgoCD SRE
---

Argo CD 部署模式影响故障域、安全边界与运维复杂度。

## 部署模式对比

| 模式 | 说明 | 适用 |
|------|------|------|
| In-cluster 单集群 | Argo CD 管本集群 | 小团队 POC |
| In-cluster HA | 多副本 + Redis HA | 单集群生产 |
| Hub-Spoke 多集群 | 中心 Argo CD 管 N 集群 | 企业标准 |
| 每集群独立 Argo CD | 完全隔离 | 强合规/多租户云 |
| 命名空间级 Argo CD | 软多租户 | 不推荐生产 |

## Hub-Spoke 架构

```
                    ┌─────────────┐
                    │  Mgmt 集群   │
                    │  Argo CD HA │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
      Prod Cluster    Staging Cluster   DR Cluster
```

**优点**：统一 GitOps 入口、统一 RBAC  
**要求**：Mgmt → Spoke API 网络、cluster secret 安全

## 组件 sizing 参考

| 规模 | Application 数 | repo-server | controller |
|------|------------------|-------------|------------|
| 小 | < 50 | 2 × 500m | 1 |
| 中 | 50~300 | 2 × 1 CPU | 1~2 shards |
| 大 | 300+ | 3+ × 2 CPU | sharding 必须 |

## 网络与访问

| 项 | 生产要求 |
|----|----------|
| UI/API | Ingress + TLS + SSO |
| Git | 出网 HTTPS 或内网 Git |
| Spoke API | 私有连接/VPN/PrivateLink |
| CLI/CI | `--grpc-web` 经 Ingress |

## 反模式

- 生产用 `install.yaml` 单副本默认配置
- Argo CD 与业务混部同节点无反亲和
- 所有环境共用一个 admin 账号

选型文档应包含：**集群清单、Git 仓策略、SSO、备份方案**。
