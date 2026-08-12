---
title: GitLab Omnibus HA 生产部署入门
date: 2026-08-29 09:30:00
tags:
  - GitLab
  - SRE
  - HA
categories:
  - GitLab SRE
---

Omnibus **多节点 HA** 是自建 GitLab 生产最常见形态。

## 节点角色（参考架构）

| 节点 | 角色 |
|------|------|
| LB ×2 | HAProxy/Nginx + Keepalived |
| App ×2 | gitlab-rails + sidekiq + gitlab-workhorse |
| Gitaly ×3 | Git 仓库存储（+ Praefect） |
| PG ×3 | Patroni PostgreSQL 集群 |
| Redis ×3 | Sentinel 或 Cluster |

## 关键 gitlab.rb（App 节点）

```ruby
external_url 'https://gitlab.example.com'
gitlab_rails['time_zone'] = 'Asia/Shanghai'

# 指向外部 PG
gitlab_rails['db_host'] = '10.0.1.10'
gitlab_rails['db_port'] = 5432
gitlab_rails['db_password'] = '<from-vault>'

# Redis Sentinel
gitlab_rails['redis_host'] = '10.0.2.10'
gitlab_rails['redis_port'] = 26379

# Gitaly Cluster
git_data_dirs({
  "default" => {
    "gitaly_address" => "tcp://praefect.internal:2305"
  }
})
```

## 部署后验收

```bash
gitlab-rake gitlab:check SANITIZE=true
gitlab-rake gitlab:doctor:secrets
curl -I https://gitlab.example.com/-/health
curl https://gitlab.example.com/-/readiness
```

## LB 健康检查

```
GET /-/health  → 200
GET /-/readiness → 200（依赖 PG/Redis/Gitaly）
```

## 反模式

- App 节点 local disk 存 Git 数据（应 Gitaly）
- 跳过 `gitlab:check` 即切流量
- 无 sticky session 导致某些操作异常（ActionCable）

HA 上线后执行 **节点故障切换演练**。
