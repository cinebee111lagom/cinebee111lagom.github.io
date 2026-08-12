---
title: Jenkins 共享库与标准化 CI
date: 2026-08-23 12:15:00
tags:
  - Jenkins
  - 共享库
categories:
  - Jenkins SRE
---

**Shared Library** 将 Pipeline 公共逻辑集中管理，是平台工程核心。

## 仓库结构

```
jenkins-shared-library/
├── vars/
│   └── standardPipeline.groovy   # 全局变量
├── src/
│   └── org/corp/
│       └── BuildUtils.groovy       # 类
└── resources/
    └── templates/
        └── Dockerfile.python
```

## vars 示例

```groovy
// vars/standardPipeline.groovy
def call(Map config) {
    pipeline {
        agent { label config.agent ?: 'docker' }
        stages {
            stage('Checkout') { steps { checkout scm } }
            stage('Test') {
                steps { sh config.testCommand ?: 'make test' }
            }
            stage('Build') {
                steps { sh config.buildCommand }
            }
        }
    }
}
```

## Jenkins 配置

```
Manage Jenkins → System → Global Pipeline Libraries
Name: corp-pipeline
Default version: main
Retrieval: Modern SCM → Git → https://git.example.com/jenkins-shared-library.git
```

## 使用

```groovy
@Library('corp-pipeline@main') _

standardPipeline(
    agent: 'docker',
    testCommand: 'pytest',
    buildCommand: 'docker build -t app .',
)
```

## 版本 pinning

```groovy
@Library('corp-pipeline@v2.3.1') _   // 生产 pin tag
```

## CasC 配置库

```yaml
unclassified:
  globalLibraries:
    libraries:
      - name: corp-pipeline
        defaultVersion: "v2.3.1"
        retriever:
          modernSCM:
            scm:
              git:
                remote: "https://git.example.com/jenkins-shared-library.git"
```

## SRE 治理

| 规则 | 说明 |
|------|------|
| Library 变更需 Code Review | 影响全公司 Pipeline |
| 语义化版本 tag | 可回滚 |
| 单元测试 | library 内 Groovy 测试 |
| 文档 | 每个 var 参数说明 |

共享库是 **CI 标准化** 的杠杆，SRE 维护库，团队消费。
