---
title: GitLab SRE 上线 Checklist 与生产 Runbook
date: 2026-08-29 13:30:00
tags:
  - GitLab
  - SRE
  - Runbook
categories:
  - GitLab SRE
---

## 上线 Checklist

### 架构

- [ ] HA：App/Gitaly/PG/Redis 无单点
- [ ] LB + TLS + 健康检查
- [ ] 对象存储（Artifacts/LFS/Registry）
- [ ] external_url 正确

### 安全

- [ ] signup 关闭、2FA 强制
- [ ] SSO 集成
- [ ] 保护分支默认配置
- [ ] Audit log 接入 SIEM

### 备份

- [ ] 每日 gitlab-backup + offsite
- [ ] gitlab-secrets.json 安全备份
- [ ] 3 个月内 restore 演练成功

### 监控

- [ ] /-/health blackbox
- [ ] Sidekiq/Gitaly/PG/Redis 指标
- [ ] P0/P1 告警 + Runbook 链接

### CI/CD

- [ ] Group Runner 池就绪
- [ ] CI 模板与治理规范发布
- [ ] Registry cleanup policy

---

## 日常 Runbook

| 频率 | 动作 |
|------|------|
| 每日 | 告警 review、Sidekiq 队列 |
| 每周 | 磁盘/Registry 用量、Runner 状态 |
| 每月 | Token 审计、备份验证 |
| 每季 | 升级 staging、restore 演练 |

## 应急

| 事件 | 动作 |
|------|------|
| 全站 502 | LB → gitlab-ctl status → 日志 |
| git 不可用 | Gitaly/Praefect 状态 |
| CI 全 pending | Runner / Sidekiq |
| 磁盘满 | Registry GC / 扩容 |

## 联系

```
GitLab SRE on-call
DBA（PG）
网络（LB/DNS）
安全（入侵/Token 泄露）
```

## 反模式

- Checklist 未勾完即推广全公司
- Runbook 无负责人
- 备份未验证 restore

配合 **GitLab 新手入门** 系列：入门用平台，SRE 保平台。
