---

## title: Jenkins SRE 上线 Checklist 与生产 Runbook
date: 2026-08-23 13:45:00
tags:
  - Jenkins
  - SRE
  - Runbook
categories:
  - Jenkins SRE

## 上线 Checklist

### 架构

- Controller HA + 共享 JENKINS_HOME（NFS/EFS）
- Controller executor = 0
- Agent 池规模与标签文档化
- HTTPS + 反向代理

### 配置

- LTS 版本 + JDK 17
- JVM 参数基线
- buildDiscarder 全局策略
- Quiet Period / 超时默认值
- JCasC 或配置备份

### 安全

- LDAP/OAuth + RBAC
- 匿名无权限、CSRF 开启
- 凭据 Folder 隔离
- Script Console 受限
- 插件最小集 + 版本锁

### 备份

- JENKINS_HOME 日备份 + 异地
- secrets/master.key 含备份
- 3 个月内 restore 演练成功
- 共享库与 Jenkinsfile 在 Git

### 监控

- Prometheus metrics + Grafana
- health/queue/offline P0/P1 告警
- 告警带 Runbook 链接

---

## 日常 Runbook

### Controller 不可访问（P0）

```bash
systemctl status jenkins
journalctl -u jenkins -n 200
df -h $JENKINS_HOME
# HA：切 standby，查 NFS mount
```

### 队列堆积（P1）

- Manage Jenkins → Build Queue 查看
- 扩 Agent / 临时加 executor
- 取消重复 webhook 触发 Job

### Agent 全部离线

- 查 50000/JNLP 网络
- Controller 是否重启导致 secret 轮换
- Agent systemd 批量重启

### 磁盘满

```bash
du -sh $JENKINS_HOME/*
# 清理 workspace、旧 builds
# 调整 discard 策略
```

### 插件/Jenkins 升级失败

```bash
# 安全模式启动，禁用问题插件
java -jar jenkins.war --httpPort=8080
# 或恢复备份 WAR + JENKINS_HOME
```

### 紧急回滚

```
1. 停止 Jenkins
2. 恢复上一版本镜像/WAR
3. restore JENKINS_HOME 备份（若必要）
4. 启动 + smoke Pipeline
```

---

**Jenkins SRE 系列 20 篇**完结，涵盖部署、HA、备份、Pipeline、Agent、安全、K8s、升级、共享库、凭据、监控与演练。建议配合 **Python 生产环境**、**Kubernetes SRE** 系列对照阅读。