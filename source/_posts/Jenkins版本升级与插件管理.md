---
title: Jenkins 版本升级与插件管理
date: 2026-08-23 12:00:00
tags:
  - Jenkins
  - 升级
categories:
  - Jenkins SRE
---

Jenkins 升级需 **LTS 轨道 + 备份 + staging 验证 + 插件兼容性矩阵**。

## 升级路径

```
仅跟随 Jenkins LTS 线
2.426 LTS → 2.440 LTS → 下一 LTS
跳过非 LTS 版本（生产）
```

## 升级前

```bash
# 1. 完整备份 JENKINS_HOME
# 2. 导出插件列表
jenkins-plugin-cli --list > plugins.txt
# 3. staging 同版本升级演练
# 4. 查 LTS Upgrade Guide
```

## 升级步骤

```bash
# Docker
docker pull jenkins/jenkins:2.452.1-lts-jdk17
# 停旧容器 → 挂载同一 volume → 启新镜像

# WAR
systemctl stop jenkins
cp jenkins.war jenkins.war.bak
curl -O https://get.jenkins.io/war-stable/latest/jenkins.war
systemctl start jenkins
```

## 插件管理

```bash
# jenkins-plugin-cli
jenkins-plugin-cli --plugins \
  kubernetes workflow-aggregator prometheus

# 锁定版本
echo "kubernetes:4246.v5a_0b_8c4e8f3" >> plugins.txt
```

| 原则 | 说明 |
|------|------|
| 最小集 | 能不用就不装 |
| 版本锁 | 与 LTS 兼容矩阵 |
| 分批升 | 先 staging 全量插件 |

## 回滚

```
恢复 jenkins.war.bak
或 Docker 回退镜像 tag
JENKINS_HOME 从备份 restore（若升级迁移失败）
```

## 常见失败

| 问题 | 解决 |
|------|------|
| 插件不兼容 | 降插件或升 Jenkins |
| 启动循环 | 插件目录 `.jpi` 冲突，安全模式启动 |
| JDK 版本 | 确保 JDK 17+ |

安全模式：`java -jar jenkins.war --httpPort=8080` 并禁用问题插件。

## Checklist

- [ ] 备份完成
- [ ] staging 验证关键 Pipeline
- [ ] 低峰窗口
- [ ] 回滚方案就绪
- [ ] 升级后跑 smoke Pipeline

**永远不要在生产直接点「Upgrade automatically」**。
