---
title: Jenkins SRE 告警规则与值班手册
date: 2026-08-23 10:45:00
tags:
  - Jenkins
  - SRE
  - 告警
categories:
  - Jenkins SRE
---

Jenkins 告警需区分平台故障与业务构建失败。

## 告警分级

| 级别 | 场景 | 响应 |
|------|------|------|
| P0 | Controller down、JENKINS_HOME 只读 | 5 分钟 |
| P1 | 全部 Agent 离线、队列 > 50 | 15 分钟 |
| P2 | 单 Agent 离线、磁盘 > 85% | 1 小时 |
| P3 | 插件更新可用、证书过期 | 工作日 |

## Prometheus 规则

```yaml
groups:
  - name: jenkins
    rules:
      - alert: JenkinsDown
        expr: jenkins_health_check_score < 1
        for: 2m
        labels:
          severity: critical

      - alert: JenkinsQueueHigh
        expr: jenkins_queue_size > 30
        for: 10m
        labels:
          severity: warning

      - alert: JenkinsNoExecutors
        expr: jenkins_executor_free == 0
        for: 15m
        labels:
          severity: warning

      - alert: JenkinsNodeOffline
        expr: jenkins_node_offline_value > 0
        for: 5m
        labels:
          severity: warning
```

## 值班速查

### Controller 不可访问

```bash
systemctl status jenkins
journalctl -u jenkins -n 200
df -h /var/jenkins_home
# HA：切 standby，查 NFS 挂载
```

### 构建全失败（平台）

- 查磁盘满、插件冲突、凭据过期
- 最近是否升级 Jenkins/插件

### 队列堆积

```bash
# Script Console 或 UI
# Manage Jenkins → Build Queue
```

- 扩 Agent、临时加 executor
- 取消异常触发的重复 Job

### Agent 离线

```bash
# Agent 节点
systemctl status jenkins-agent
java -jar agent.jar ...   # 手动测试连接
# 查 50000 端口、JENKINS_URL、secret
```

### 磁盘满

- 清理 workspace、旧构建（Discarder）
- 扩 NFS/磁盘

## 区分业务失败

```
平台告警：health、queue、offline
业务告警：特定 Job 连续失败 → 通知开发 Owner
```

## On-Call 原则

1. Controller 恢复优先于单 Job
2. 插件回滚比盲升更稳
3. 变更窗口升级，48h Postmortem

每季度 review 告警，**Job 失败默认不走 P0**（除非发布流水线）。
