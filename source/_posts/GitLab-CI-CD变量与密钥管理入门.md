---
title: GitLab CI/CD 变量与密钥管理入门
date: 2026-08-28 11:00:00
tags:
  - GitLab
  - 变量
  - 入门
categories:
  - GitLab 新手入门
---

敏感信息用 **CI/CD Variables**，绝不写进 `.gitlab-ci.yml` 明文。

## 变量层级（优先级高→低）

```
Job 内 variables
  ← Project CI/CD Variables
  ← Group CI/CD Variables
  ← Instance Variables
```

## 添加变量

**Settings → CI/CD → Variables**

| 选项 | 说明 |
|------|------|
| Key | 如 `DOCKER_PASSWORD` |
| Value | 密钥内容 |
| Protect | 仅保护分支 Pipeline 可用 |
| Mask | 日志中打码 |
| Expand | 是否展开变量引用 |

## 使用变量

```yaml
deploy:
  script:
    - echo "$CI_REGISTRY_PASSWORD" | docker login -u "$CI_REGISTRY_USER" --password-stdin $CI_REGISTRY
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  variables:
    DOCKER_TLS_CERTDIR: ""
```

## 预定义常用变量

| 变量 | 用途 |
|------|------|
| CI_REGISTRY_USER | Registry 登录 |
| CI_REGISTRY_PASSWORD | Registry 密码 |
| CI_JOB_TOKEN | 跨项目 API/clone |
| CI_DEPLOY_USER | 部署只读用户 |

## .env 文件（不推荐进 Git）

```yaml
# 从 File 类型变量加载
job:
  script:
    - export $(cat $ENV_FILE | xargs)
```

Variable 类型选 **File**，GitLab 写入临时文件。

## 反模式

- Secret 写在 script echo
- Mask 变量过短（< 8 字符无法 mask）
- 生产密钥不勾 Protect

下一篇：**Docker 镜像构建与推送**。
