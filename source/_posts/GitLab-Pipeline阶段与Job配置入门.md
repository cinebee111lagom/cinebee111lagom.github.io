---
title: GitLab Pipeline 阶段与 Job 配置入门
date: 2026-08-28 10:45:00
tags:
  - GitLab
  - Pipeline
  - 入门
categories:
  - GitLab 新手入门
---

合理设计 **Stage/Job** 让流水线又快又稳。

## 典型 Stage 划分

```yaml
stages:
  - lint
  - build
  - test
  - deploy
```

| Stage | Job 示例 |
|-------|----------|
| lint | eslint、golint |
| build | docker build、npm build |
| test | unit、e2e |
| deploy | staging/prod |

## Job 完整配置示例

```yaml
unit-test:
  stage: test
  image: node:20
  script:
    - npm ci
    - npm run test:coverage
  coverage: '/Lines\s*:\s*(\d+\.\d+)%/'
  artifacts:
    when: always
    reports:
      junit: report.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == "main"
```

## 并行与依赖

```yaml
# 同 stage 并行
test-unit:
  stage: test
  script: npm run test:unit

test-e2e:
  stage: test
  script: npm run test:e2e

# 跨 job 依赖 artifacts
deploy:
  stage: deploy
  needs:
    - job: build
      artifacts: true
  script:
    - deploy dist/
```

`needs` 可跳过 stage 顺序，加速 Pipeline。

## 失败策略

```yaml
test:
  retry:
    max: 2
    when: runner_system_failure

deploy:
  when: on_success   # 默认
  allow_failure: false
```

## 超时

```yaml
job:
  timeout: 30m
```

## include 复用

```yaml
include:
  - local: '/ci/build.yml'
  - project: 'mygroup/ci-templates'
    file: '/docker-build.yml'
```

## 反模式

- deploy 与 test 同 stage
- 无 artifacts 重复 build
- 单 Job 跑 2 小时无 timeout

下一篇：**变量与密钥管理**。
