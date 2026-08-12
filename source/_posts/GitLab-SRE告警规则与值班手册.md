---
title: GitLab SRE 告警规则与值班手册
date: 2026-08-29 10:15:00
tags:
  - GitLab
  - SRE
  - 告警
categories:
  - GitLab SRE
---

## P0 告警

```yaml
- alert: GitLabDown
  expr: probe_success{job="blackbox-gitlab-health"} == 0
  for: 5m

- alert: GitLabReadinessFailed
  expr: gitlab_readiness < 1
  for: 5m

- alert: GitalyDown
  expr: up{job="gitaly"} == 0
  for: 2m

- alert: GitLabPostgreSQLDown
  expr: pg_up == 0
  for: 2m
```

## P1 告警

```yaml
- alert: SidekiqQueueBacklog
  expr: sum(sidekiq_queue_size) > 10000
  for: 15m

- alert: GitLabHighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 10m

- alert: GitLabDiskSpaceLow
  expr: node_filesystem_avail_bytes{mountpoint="/var/opt/gitlab"} / node_filesystem_size_bytes < 0.15
  for: 30m

- alert: GitLabRunnerOffline
  expr: gitlab_runner_concurrent < 1
  for: 10m

- alert: CIPipelineFailureSpike
  expr: rate(gitlab_ci_pipeline_failure_total[15m]) > 0.5
  for: 15m
```

## 值班 Runbook

| 告警 | 第一步 | 第二步 |
|------|--------|--------|
| GitLabDown | LB/证书/DNS | `gitlab-ctl status` |
| Sidekiq 积压 | queue 名称 | 扩容 sidekiq / 查 stuck job |
| Gitaly 慢 | 磁盘 IO | gitaly 日志 / 仓大小 |
| 磁盘满 | Registry/Artifacts 清理 | 扩容 / 对象存储迁移 |
| Runner 离线 | runner verify | 节点/标签/并发数 |

## 通知

```
P0 → 电话 + IM（5 分钟）
P1 → IM + 工单（30 分钟）
```

## 反模式

- 仅监控 HTTP 不监控 Sidekiq/Gitaly
- CI 失败率告警无区分（含用户脚本错误）
- 无 Runbook 链接

每季度 **模拟 PG failover** 验证告警。
