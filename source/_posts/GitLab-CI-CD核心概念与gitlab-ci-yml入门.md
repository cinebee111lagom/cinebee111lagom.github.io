---
title: GitLab CI/CD 核心概念与 .gitlab-ci.yml 入门
date: 2026-08-28 10:15:00
tags:
  - GitLab
  - CI/CD
  - 入门
categories:
  - GitLab 新手入门
---

GitLab CI 用根目录 **`.gitlab-ci.yml`** 定义流水线，提交即触发。

## 核心概念

| 概念 | 说明 |
|------|------|
| Pipeline | 一次完整 CI 运行 |
| Stage | 阶段（build → test → deploy） |
| Job | 阶段内的具体任务 |
| Runner | 执行 Job 的代理 |
| Artifact | Job 产出文件传递 |
| Cache | 依赖缓存加速 |

## 最小示例

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test

build-job:
  stage: build
  script:
    - echo "Building..."
    - npm install
    - npm run build
  artifacts:
    paths:
      - dist/

test-job:
  stage: test
  script:
    - npm test
```

## 执行顺序

```
push/MR → Pipeline 创建
  → build-job（stage: build）
  → test-job（stage: test，build 成功后）
```

同 Stage 内 Job **并行**，Stage 间 **串行**。

## 触发规则

```yaml
# 仅 main 分支 deploy
deploy:
  stage: deploy
  script:
    - ./deploy.sh
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

## 常用内置变量

| 变量 | 含义 |
|------|------|
| CI_COMMIT_SHA | 当前 commit |
| CI_COMMIT_BRANCH | 分支名 |
| CI_PROJECT_NAME | 项目名 |
| CI_PIPELINE_ID | Pipeline ID |
| CI_REGISTRY | 内置 Registry 地址 |

## 查看 Pipeline

**Build → Pipelines** 或 MR 页面的 Pipeline 状态。

## 反模式

- `.gitlab-ci.yml` 语法错误无本地验证
- 所有 Job 放一个 stage 失去并行
- script 里写明文密码

下一篇：**GitLab Runner 安装与注册**。
