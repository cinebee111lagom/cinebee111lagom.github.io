---
title: Jenkins Pipeline 生产最佳实践
date: 2026-08-23 11:00:00
tags:
  - Jenkins
  - Pipeline
categories:
  - Jenkins SRE
---

Declarative Pipeline + Jenkinsfile 是生产标准，SRE 需推动规范与模板化。

## 标准 Jenkinsfile 结构

```groovy
pipeline {
    agent { label 'docker' }

    options {
        buildDiscarder(logRotator(numToKeepStr: '20', daysToKeepStr: '60'))
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        REGISTRY = 'registry.example.com'
        IMAGE = "${REGISTRY}/${JOB_NAME}:${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Test') {
            steps { sh 'make test' }
            post {
                always { junit 'reports/*.xml' }
            }
        }
        stage('Build & Push') {
            steps {
                sh 'docker build -t $IMAGE .'
                sh 'docker push $IMAGE'
            }
        }
        stage('Deploy Staging') {
            when { branch 'main' }
            steps { sh './deploy.sh staging $IMAGE' }
        }
    }

    post {
        failure {
            slackSend channel: '#ci-alerts', message: "Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        }
        success {
            cleanWs()
        }
    }
}
```

## 生产规范

| 规范 | 原因 |
|------|------|
| Jenkinsfile 入 Git | 版本化、Review |
| 固定 agent label | 资源可控 |
| timeout | 防 hung build |
| disableConcurrentBuilds | 防资源争抢（视场景） |
| post always cleanWs | 防磁盘涨 |
| 凭据用 credentials() | 不写明文 |

## 多分支 Pipeline

```groovy
pipeline {
    agent none
    stages {
        stage('PR') {
            when { changeRequest() }
            agent { label 'small' }
            steps { sh 'make test' }
        }
        stage('Main') {
            when { branch 'main' }
            agent { label 'docker' }
            steps { sh 'make deploy' }
        }
    }
}
```

## 共享库

```groovy
@Library('corp-pipeline@v2') _
standardPipeline(
    language: 'python',
    deployEnvs: ['staging', 'prod'],
)
```

## SRE 治理

- Golden Pipeline 模板入库
- 禁止 Script Console 随意执行（RBAC）
- 构建节点禁止 `--privileged` 除非审批

Pipeline 是**交付路径代码化**，SRE 管平台，开发管 Stage 逻辑。
