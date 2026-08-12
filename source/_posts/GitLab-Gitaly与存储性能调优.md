---
title: GitLab Gitaly 与存储性能调优
date: 2026-08-29 12:00:00
tags:
  - GitLab
  - SRE
  - Gitaly
categories:
  - GitLab SRE
---

**Gitaly** 负责所有 Git 读写，慢 push/clone 多半在存储层。

## 架构

```
gitlab-workhorse → gitaly（单节点）
                 → praefect → gitaly × N（Cluster，HA）
```

生产 **>100 用户** 建议 Gitaly Cluster + Praefect。

## 磁盘要求

| 项 | 建议 |
|----|------|
| 类型 | SSD/NVMe |
| IOPS | 高随机读写 |
| 容量 | 仓大小 × 1.5 + 增长 |
| 监控 | latency、iowait、空间 |

## 大仓治理

| 问题 | 措施 |
|------|------|
| 单仓 >5GB | LFS、history 清理 |
| 大 blob | BFG / git filter-repo |
| 单项目慢 | `gitaly check` |

```bash
# 仓大小 Top N
gitlab-rake gitlab:git:list_large_repositories
```

## gitaly 调优

```ruby
gitaly['configuration'] = {
  concurrency: [
    { 'rpc' => '/gitaly.SmartHTTPService/PostReceivePack', 'max_per_repo' => 3 }
  ],
  cgroups: {
    mountpoint: '/sys/fs/cgroup',
    repositories: { count: 1000, memory_bytes: 1073741824 }
  }
}
```

## 反模式

- HDD 跑生产 Gitaly
- 巨型 monorepo 无 LFS
- 不监控 gitaly grpc latency

Gitaly 故障 → **全站 git 不可用，P0**。
