---
title: GitLab CI/CD 生产流水线治理
date: 2026-08-29 11:15:00
tags:
  - GitLab
  - SRE
  - CI/CD
categories:
  - GitLab SRE
---

平台 SRE 需治理 **流水线规范、资源消耗与发布安全**。

## 组织级 CI 模板

```yaml
# .gitlab/ci-templates/docker-build.yml
.docker-build:
  image: docker:24
  services: [docker:24-dind]
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

Group **CI/CD Catalog** 或 include 统一模板。

## 治理规则

| 规则 | 实现 |
|------|------|
| 禁止 main 直接 push | 保护分支 |
| MR 必须 CI 绿 | Merge checks |
| prod deploy 仅 main | rules + environment |
| 密钥不进 YAML | CI Variables Mask |
| 超时上限 | default timeout 1h |

## 资源配额

**Admin → Settings → CI/CD → Continuous Integration**

- Default artifacts expiration
- Maximum artifacts size
- Pipeline schedule 限制

## 恶意 MR 防护

- Fork MR 不授予 secrets（`protected: true` variables）
- 需 Maintainer 批准才跑 deploy job
- `CI_JOB_TOKEN` 权限最小化

## 流水线效率

```yaml
workflow:
  rules:
    - if: $CI_COMMIT_MESSAGE =~ /\[skip ci\]/
      when: never
    - when: always

# 快反馈
stages: [lint, test, build, deploy]
```

## 指标

| 指标 | 目标 |
|------|------|
| MR pipeline 时长 P95 | < 15min |
| 队列等待 | < 5min |
| 失败率（平台原因） | < 1% |

## 反模式

- 无 include 每项目复制 200 行 CI
- prod deploy job 无 manual/environment
- Fork 泄露 Protected Variables

治理文档 + **lint CI（ci lint API）** 进 MR 检查。
