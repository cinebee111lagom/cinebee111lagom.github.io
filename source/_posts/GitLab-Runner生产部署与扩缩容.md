---
title: GitLab Runner 生产部署与扩缩容
date: 2026-08-29 11:00:00
tags:
  - GitLab
  - SRE
  - Runner
categories:
  - GitLab SRE
---

Runner 是 CI **算力池**，SRE 负责可用性、隔离与容量。

## 生产 Runner 架构

| 类型 | 部署 | 适用 |
|------|------|------|
| Group Runner | K8s / VM 池 | 团队共享 |
| Project Runner | 专用节点 | 敏感/高负载 |
| K8s executor | GitLab Runner Operator | 弹性伸缩 |

## 注册（Group Runner）

```bash
gitlab-runner register \
  --url https://gitlab.example.com \
  --token <group-runner-token> \
  --executor docker \
  --docker-image docker:24 \
  --description "prod-docker-pool" \
  --tag-list "docker,linux,prod" \
  --run-untagged=false \
  --locked=true
```

## config.toml 生产配置

```toml
concurrent = 50
check_interval = 3

[[runners]]
  name = "prod-docker"
  limit = 20
  [runners.docker]
    tls_verify = false
    image = "docker:24"
    privileged = true
    pull_policy = ["if-not-present"]
  [runners.cache]
    Type = "s3"
    Path = "gitlab-runner-cache"
    Shared = true
```

## K8s 弹性

```yaml
# runner autoscaler：queue 深度 → 增 Pod
runners:
  config: |
    [[runners]]
      [runners.kubernetes]
        namespace = "gitlab-runner"
        cpu_limit = "2"
        memory_limit = "4Gi"
```

## 监控

| 指标 | 告警 |
|------|------|
| runner_concurrent 满 | 扩容 |
| job 等待 > 10min | P1 |
| runner 离线 | P1 |

## 安全

- 不可信代码 **禁止 shell executor 共享宿主机**
- docker executor 隔离 + 定期清 image
- `--run-untagged=false` 防误用

## 反模式

- 全员共用一个无 tag Runner
- privileged 无网络隔离跑 PR 代码
- 无 cache 导致每次 npm ci 极慢

Runner 容量按 **峰值 concurrent job × 资源** 规划。
