---
title: GitLab 版本升级与滚动迁移 SRE 流程
date: 2026-08-29 10:45:00
tags:
  - GitLab
  - SRE
  - 升级
categories:
  - GitLab SRE
---

GitLab **严格版本路径**，不可跨 major 跳跃，升级需维护窗口。

## 升级路径

```
16.11.x → 17.0.x → 17.11.x → 18.0.x
（每次只升下一个 minor，读 Release Notes）
```

## 升级前 Checklist

- [ ] 阅读 Upgrade Path 文档
- [ ] 全量备份 + secrets
- [ ] staging 同路径验证
- [ ] 检查 PostgreSQL/Redis 版本要求
- [ ] 通知用户维护窗口

## Omnibus 升级

```bash
# 备份
gitlab-backup create

# 升级包（Ubuntu 示例）
apt update
apt install gitlab-ce=<target-version>

gitlab-ctl reconfigure
gitlab-ctl restart
gitlab-rake gitlab:check
gitlab-rake db:migrate:status
```

## HA 滚动升级

```
1. 升级 Gitaly/PG/Redis（按依赖顺序）
2. 逐台 App 节点：stop → upgrade → reconfigure → start
3. LB 摘除/加回
4. 验证 /-/health、push、MR、Pipeline
```

## 回滚

- 保留上一版本 package
- restore backup（数据已 migrate 时回滚难，**staging 必须先测**）
- Geo 环境先升 secondary

## 反模式

- 跳过多个 minor
- 无备份直接 upgrade
- 升级日合并大量 CI 变更

升级记录：**版本、耗时、问题、回滚与否**。
