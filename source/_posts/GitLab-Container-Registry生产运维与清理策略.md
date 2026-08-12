---
title: GitLab Container Registry 生产运维与清理策略
date: 2026-08-29 11:30:00
tags:
  - GitLab
  - SRE
  - Registry
categories:
  - GitLab SRE
---

Registry 磁盘增长是 GitLab **最常见容量事故**之一。

## 存储后端

```ruby
# 生产推荐对象存储
registry['storage'] = {
  's3' => {
    'bucket' => 'gitlab-registry',
    'region' => 'cn-hangzhou',
    ...
  }
}
```

本地 disk 仅适合小规模。

## 清理策略

**Settings → Packages and registries → Cleanup policies**

```json
{
  "cadence": "1d",
  "older_than": "30d",
  "keep_n": 10,
  "name_regex": ".*",
  "name_regex_keep": "main|release-.*"
}
```

## 手动 GC（Omnibus）

```bash
gitlab-ctl registry-garbage-collect -m
# 维护窗口执行，可能耗时数小时
```

## 监控

| 指标 | 告警 |
|------|------|
| registry 存储用量 | > 80% |
| push 失败率 | 升高 |
| layer upload 超时 | 磁盘/网络 |

## 与 K8s 拉取

- 使用 **Deploy Token** 或 **CI_JOB_TOKEN** 作用域
- 镜像 tag 用 `$CI_COMMIT_SHA`，非仅 latest
- Harbor/ACR 同步（可选二级缓存）

## Runbook：磁盘满

```
1. 紧急：cleanup policy 加速 + 删 untagged
2. registry-garbage-collect
3. 迁移 S3
4. 审计大镜像项目
```

## 反模式

- 无 cleanup 策略
- 所有 tag 永久保留
- GC 从未跑过

Registry 用量 **周报 + 按 Group 分摊**。
