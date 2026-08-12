---
title: Jenkins Agent 管理与扩缩容
date: 2026-08-23 11:15:00
tags:
  - Jenkins
  - Agent
categories:
  - Jenkins SRE
---

Agent 是构建算力来源，SRE 需保障**可用性、隔离与弹性**。

## Agent 类型对比

| 类型 | 扩缩 | 隔离 | 维护 |
|------|------|------|------|
| 静态 VM | 手动 | 中 | 中 |
| Docker | 中等 | 高 | 低 |
| K8s Pod | 自动 | 最高 | 中 |

## K8s 动态 Agent

```groovy
pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: builder
    image: registry.example.com/buildkit:1.0
    command: ["sleep"]
    args: ["99999"]
    resources:
      requests: { cpu: "1", memory: "2Gi" }
      limits:   { cpu: "2", memory: "4Gi" }
'''
        }
    }
    stages {
        stage('Build') {
            steps {
                container('builder') {
                    sh 'make build'
                }
            }
        }
    }
}
```

## 节点标签策略

```
docker     → Docker 构建
linux-large → 大内存编译
windows    → .NET 构建
```

Job 通过 `agent { label 'docker' }` 匹配。

## 扩缩触发

| 信号 | 动作 |
|------|------|
| queue > 10 持续 | K8s 增 Pod template 副本 / 启 VM |
| executor 长期 0 空闲 | 缩容 Agent 降成本 |
| 构建超时多 | 查 Agent 资源 limit |

## Agent 磁盘

```bash
# workspace 定期清理
find /data/jenkins/workspace -mtime +7 -delete
```

Jenkinsfile `cleanWs()` + 节点 cron。

## 离线排查

```
1. Agent 日志
2. JNLP secret 是否轮换
3. 网络 50000 / JNLP443
4. Java 版本与 Controller 一致（JDK 17）
```

## Checklist

- [ ] Controller executor=0
- [ ] Agent 资源 limit 已设
- [ ] 标签规范文档化
- [ ] K8s Pod 非 privileged（默认）
- [ ] 镜像版本固定 digest

**队列长 = Agent 不足或构建太慢**，先量化再扩容。
