---
title: Jenkins 备份与灾难恢复
date: 2026-08-23 10:15:00
tags:
  - Jenkins
  - 备份
categories:
  - Jenkins SRE
---

Jenkins 状态集中在 **JENKINS_HOME**，备份与恢复围绕此目录展开。

## JENKINS_HOME 关键内容

```
JENKINS_HOME/
├── config.xml           # 全局配置
├── jobs/                # Job 定义与构建历史
├── users/               # 用户
├── credentials.xml      # 凭据（加密）
├── secrets/             # 密钥材料
├── plugins/             # 插件
└── workspace/           # 工作区（可选不备份）
```

## 备份策略

| 方式 | 频率 | 保留 |
|------|------|------|
| NFS 快照 | 每日 | 30 天 |
| rsync/tar 异地 | 每日 | 90 天 |
| CasC + Job DSL Git | 实时 | 永久 |
| ThinBackup 插件 | 每日 | 可配置 |

## 脚本备份

```bash
#!/bin/bash
BACKUP_DIR=/backup/jenkins/$(date +%Y%m%d)
JENKINS_HOME=/var/jenkins_home

systemctl stop jenkins   # 或热备份（ThinBackup）
mkdir -p "$BACKUP_DIR"
tar czf "$BACKUP_DIR/jenkins_home.tar.gz" \
  --exclude=workspace \
  --exclude=workspace@tmp \
  --exclude=cache \
  "$JENKINS_HOME"
aws s3 cp "$BACKUP_DIR/jenkins_home.tar.gz" s3://backup-bucket/jenkins/
systemctl start jenkins
```

## Configuration as Code（推荐补充）

```yaml
# jenkins.yaml + credentials 引用 K8s Secret
# Job 定义用 Job DSL 或 Jenkinsfile 在 Git
```

Git 存配置，JENKINS_HOME 备份存**构建历史与凭据**。

## 恢复流程

```
1. 新 Controller 挂载空 JENKINS_HOME
2. 解压备份 tar 到 JENKINS_HOME
3. chown jenkins:jenkins
4. 启动 Jenkins，验证插件版本
5. Agent 重连，试跑关键 Pipeline
```

## RPO/RTO

| 方案 | RPO | RTO |
|------|-----|-----|
| 日备份 | 24h | 1~2h |
| NFS 快照 | 1h | 30min |
| CasC + Git Jobs | 分钟级 | 15min（无历史） |

## Checklist

- [ ] 备份排除 workspace（减体积）
- [ ] credentials 加密 master key 一并备份 secrets/
- [ ] 季度 restore 演练
- [ ] 插件版本清单归档

**没有 restore 演练的备份不可信**。
