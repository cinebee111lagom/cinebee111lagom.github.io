---
title: Jenkins 构建缓存与性能优化
date: 2026-08-23 12:30:00
tags:
  - Jenkins
  - 性能
categories:
  - Jenkins SRE
---

构建慢影响交付效率，SRE 需从**缓存、Agent 资源、Pipeline 设计**优化。

## 依赖缓存

### Docker layer cache

```groovy
stage('Build') {
    steps {
        sh '''
          docker build \
            --cache-from registry.example.com/myapp:latest \
            -t registry.example.com/myapp:${BUILD_NUMBER} .
        '''
    }
}
```

### Maven/Gradle/npm 缓存

```groovy
// 静态 Agent 本地目录
environment {
    MAVEN_OPTS = "-Dmaven.repo.local=/cache/maven"
}
// 或 K8s PVC 挂载 /cache
```

## 并行 Stage

```groovy
stage('Tests') {
    parallel {
        stage('Unit') { steps { sh 'make unit' } }
        stage('Lint') { steps { sh 'make lint' } }
        stage('SAST') { steps { sh 'make sast' } }
    }
}
```

## 浅克隆

```groovy
checkout([
    $class: 'GitSCM',
    branches: [[name: '*/main']],
    extensions: [[$class: 'CloneOption', depth: 1, shallow: true]],
])
```

## 资源匹配

| 构建类型 | Agent |
|----------|-------|
| 小项目 | label small, 1C2G |
| Docker 镜像 | label docker, 2C4G |
| 大型编译 | label large, 8C16G |

避免小 Job 占大节点。

## 队列优化

- 合并 webhook（Quiet Period）
- 非紧急 Job 夜间 cron
- `throttle([])` 限制并发占满 executor

## 监控优化效果

```
构建时长 P50/P95 趋势
queue duration
executor utilization
```

目标：P95 构建时长季度降 20%。

## Checklist

- [ ] 依赖缓存持久化
- [ ] Docker cache-from 启用
- [ ] 并行测试
- [ ] shallow clone 默认
- [ ] 慢 Job Top 10 季度 review

**先 profile 最慢 Stage，再投资源**。
