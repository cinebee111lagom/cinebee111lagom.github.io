---
title: Jenkins 容量规划与基准测试
date: 2026-08-23 13:30:00
tags:
  - Jenkins
  - 容量规划
categories:
  - Jenkins SRE
---

Jenkins 容量需规划 **Executor 数、Agent 资源、JENKINS_HOME 磁盘与 Controller 内存**。

## Executor 容量

```
峰值并发构建数 = 同时触发的 Job 数（PR + 定时 + 发布）
所需 Executor ≥ 峰值并发 × 1.2 余量
```

例：峰值 30 并发 → 36 executor（3 节点 × 12 executor）

## Agent 资源

| 构建类型 | CPU | 内存 | 磁盘/workspace |
|----------|-----|------|----------------|
| 轻量单测 | 1C | 2G | 10G |
| Docker build | 2C | 4G | 50G |
| 大型编译 | 8C | 16G | 100G |

## JENKINS_HOME 磁盘

```
磁盘 ≈ 构建历史 + artifacts + 插件
     + 日增量 × 保留天数

控制：
  - buildDiscarder
  - 不 archive 大 artifact 到 Jenkins（用 S3/Nexus）
  - workspace 不备份
```

## Controller 内存

```
基础 2GB + 每 100 Job 约 100~200MB + 插件开销
推荐：4~8GB heap，监控 GC
```

## 基准测试

```
1. 选代表 Pipeline（docker build + test）
2. 单 Agent 串行 10 次，记 P50 时长
3. 逐步加压并发直到 queue > 0 持续
4. 记录 executor 利用率 plateau
```

## 扩容信号

| 信号 | 动作 |
|------|------|
| queue P95 > 10min | 加 Agent |
| executor 利用率 > 85% | 加 executor |
| JENKINS_HOME > 70% | discard 策略 / 扩盘 |
| Controller GC 频繁 | 增 heap / 减 Job 历史 |

## 容量报告

```
集群：jenkins-prod
Controller：4C8G，JENKINS_HOME 500G（62% used）
Agent：8 × (4C8G)，executor 64
峰值并发：28（Black Friday 模拟）
余量：executor 28%
结论：大促前 +4 Agent
```

## Checklist

- [ ] 峰值并发已压测
- [ ] artifact 外置对象存储
- [ ] 磁盘增长月度 forecast
- [ ] 大促前容量 review

容量规划避免 **发布日队列爆炸**。
