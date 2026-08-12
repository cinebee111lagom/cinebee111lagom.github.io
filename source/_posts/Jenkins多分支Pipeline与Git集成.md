---
title: Jenkins 多分支 Pipeline 与 Git 集成
date: 2026-08-23 13:00:00
tags:
  - Jenkins
  - Git
  - 多分支
categories:
  - Jenkins SRE
---

**Multibranch Pipeline** 自动发现分支/PR，是现代 Jenkins 与 Git 集成的标准。

## 创建 Multibranch Job

```
New Item → Multibranch Pipeline
Branch Sources → Git / GitHub / GitLab
  Repository URL: https://git.example.com/org/service.git
  Credentials: git-ssh-key
Behaviors:
  - Discover branches
  - Discover pull requests
Build Configuration: by Jenkinsfile
```

## Jenkinsfile 位置

```
repo/
├── Jenkinsfile          # 根目录默认
├── ci/Jenkinsfile       # 可自定义 Script Path
```

## Webhook 配置

```
GitHub/GitLab → POST https://jenkins.example.com/github-webhook/
```

Jenkins 需 **Reverse Proxy 正确转发**，CSRF 对 webhook 例外配置。

## PR 构建

```groovy
pipeline {
    agent { label 'docker' }
    stages {
        stage('Test') {
            when { changeRequest() }
            steps { sh 'make test' }
        }
        stage('Deploy') {
            when { branch 'main' }
            steps { sh 'make deploy' }
        }
    }
}
```

## 扫描间隔 vs Webhook

| 方式 | 延迟 | 负载 |
|------|------|------|
| Webhook | 秒级 | 低（推荐） |
| 定时 scan | 分钟~小时 | 高 |

## 孤儿分支清理

```
Orphaned Item Strategy: 7 天无 commit 删除 Job
```

## Monorepo

```groovy
// 使用 Path Filter 或 separate Jenkinsfile per module
when {
    changeset "services/payment/**"
}
```

## SRE 注意

- Webhook secret 验证
- Multibranch 索引失败告警
- 大 repo scan 耗 CPU，调 `Scan Multibranch Pipeline Triggers`

Multibranch 让 **每个分支自带 CI**，SRE 管平台，团队管 Jenkinsfile。
