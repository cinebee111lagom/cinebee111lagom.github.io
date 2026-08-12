---
title: GitLab 生产部署架构选型指南
date: 2026-08-29 09:15:00
tags:
  - GitLab
  - SRE
  - 架构
categories:
  - GitLab SRE
---

GitLab 生产部署方式决定 **扩展性、运维复杂度与 HA 能力**。

## 部署模式对比

| 模式 | 优点 | 缺点 | 适用 |
|------|------|------|------|
| Omnibus 单节点 | 简单 | 无 HA | POC |
| Omnibus 多节点 HA | 官方成熟 | 组件多 | 中大型自建 |
| GitLab Helm Chart | K8s 原生 | 复杂度高 | 已有 K8s 平台 |
| GitLab.com SaaS | 免运维 | 合规/成本 | 多数中小企业 |
| 分片 Geo | 异地读/灾备 | 配置复杂 | 跨国企业 |

## Omnibus HA 组件

```
Load Balancer
    ├── gitlab-rails（Web/API）
    ├── sidekiq（后台任务）
    ├── gitaly（Git 存储）
    ├── praefect（Gitaly 路由，Cluster）
    ├── patroni（PostgreSQL HA）
    └── redis-sentinel / redis-cluster
```

## 规模参考

| 用户规模 | 建议 |
|----------|------|
| < 100 | 单节点或 SaaS |
| 100~500 | 8C16G + 外部 PG/Redis |
| 500~2000 | 全 HA + Gitaly Cluster |
| 2000+ | 分片、Geo、专用 Runner 池 |

## 对象存储

生产 **附件、LFS、Registry、CI Artifacts** 应走 S3/OSS：

```ruby
# gitlab.rb
gitlab_rails['object_store']['enabled'] = true
gitlab_rails['object_store']['connection'] = {
  'provider' => 'AWS',
  'region' => 'cn-hangzhou',
  'endpoint' => 'https://oss-cn-hangzhou.aliyuncs.com',
  ...
}
```

## 反模式

- 生产单节点无备份
- 磁盘本地存 Registry 无清理
- HA 仍用内置 SQLite（应 PostgreSQL）

选型文档含：**用户数、项目数、日 Pipeline 量、RPO/RTO**。
