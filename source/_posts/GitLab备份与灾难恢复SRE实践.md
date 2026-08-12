---
title: GitLab 备份与灾难恢复 SRE 实践
date: 2026-08-29 10:30:00
tags:
  - GitLab
  - SRE
  - 备份
categories:
  - GitLab SRE
---

GitLab 丢数据等于丢 **代码 + CI 历史 + Registry**，备份是 SRE 红线。

## Omnibus 备份

```bash
# 全量备份（PG + repos + uploads + registry 等）
gitlab-backup create

# 指定策略
gitlab-backup create STRATEGY=copy

# 备份目录（默认）
/var/opt/gitlab/backups/
```

**同时备份** secrets：

```bash
cp /etc/gitlab/gitlab-secrets.json /secure/backup/
cp /etc/gitlab/gitlab.rb /secure/backup/
```

## 定时任务

```cron
0 2 * * * gitlab-backup create CRON=1
15 2 * * * aws s3 sync /var/opt/gitlab/backups/ s3://my-gitlab-backups/
```

## 恢复演练

```bash
# 停止写入
gitlab-ctl stop puma
gitlab-ctl stop sidekiq

gitlab-backup restore BACKUP=<timestamp>

gitlab-ctl reconfigure
gitlab-ctl restart
gitlab-rake gitlab:check
```

**每季度 restore 到隔离环境**，验证 RTO。

## 对象存储场景

Git 仓在 Gitaly、Artifacts 在 S3 时，备份策略：

| 组件 | 方式 |
|------|------|
| PostgreSQL | pg_dump / backup create |
| Gitaly | backup create + 磁盘快照 |
| S3 对象 | 跨区复制 / 版本控制 |
| gitlab-secrets | 离线加密备份 |

## RPO/RTO 目标

| 级别 | RPO | RTO |
|------|-----|-----|
| 标准 | 24h | 4h |
| 严格 | 1h | 1h（需连续归档） |

## 反模式

- 备份不 offsite
- 从未 restore 演练
- secrets 与 backup 放同一磁盘

备份失败 **P0 告警**，无备份不上生产。
