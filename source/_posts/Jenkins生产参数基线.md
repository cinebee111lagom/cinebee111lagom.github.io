---
title: Jenkins 生产参数基线
date: 2026-08-23 10:00:00
tags:
  - Jenkins
  - 参数
categories:
  - Jenkins SRE
---

Jenkins 生产参数覆盖 JVM、Executor、保留策略与安全基线。

## JVM（Controller 8GB 内存示例）

```bash
JAVA_OPTS="-Xms2g -Xmx4g \
  -XX:+UseG1GC \
  -XX:+AlwaysPreTouch \
  -Djava.awt.headless=true \
  -Djenkins.model.Jenkins.locationURL=https://jenkins.example.com/ \
  -Dhudson.model.DirectoryBrowserSupport.CSP=\"sandbox allow-scripts; default-src 'self';\""
```

## 全局安全配置

| 项 | 生产值 |
|----|--------|
| 启用安全 | ✅ |
| CSRF Protection | ✅ Default Crumb Issuer |
| Agent → Controller | 50000 端口限制内网 |
| 匿名用户 | 无权限 |
| Markup Formatter | Safe HTML 或 Plain Text |

## Executor 规划

```
Controller executor = 0   # 禁止 Controller 跑构建
Agent executor = 2~4/核   # 视构建类型
```

**Manage Jenkins → Configure System → # of executors = 0**

## 构建丢弃策略

```groovy
// Jenkinsfile 或 Job 配置
options {
    buildDiscarder(logRotator(numToKeepStr: '30', daysToKeepStr: '90'))
    timeout(time: 60, unit: 'MINUTES')
    timestamps()
}
```

## 插件管理

- 仅安装必要插件
- **Update Center** 固定 LTS 兼容版本
- 插件变更需 staging 验证

## 系统消息与 Quiet Period

```
SCM Quiet Period: 5s（防 webhook 风暴重复触发）
```

## CasC 基线片段

```yaml
# jenkins.yaml
jenkins:
  numExecutors: 0
  scmCheckoutRetryCount: 3
  mode: NORMAL
  securityRealm:
    ldap:
      configurations:
        - server: ldap://ldap.example.com
  authorizationStrategy:
    roleBased:
      roles:
        global:
          - name: admin
            permissions: ["Overall/Administer"]
```

参数变更记录变更单，**插件升级与 Jenkins 升级同窗口**。
