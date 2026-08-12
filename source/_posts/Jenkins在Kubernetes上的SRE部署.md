---
title: Jenkins 在 Kubernetes 上的 SRE 部署
date: 2026-08-23 11:45:00
tags:
  - Jenkins
  - Kubernetes
categories:
  - Jenkins SRE
---

K8s 部署 Jenkins 常用 **Helm Chart** 或 **Operator**，动态 Agent 是核心优势。

## Helm 安装 Controller

```bash
helm repo add jenkins https://charts.jenkins.io
helm install jenkins jenkins/jenkins -n ci -f values.yaml
```

```yaml
# values.yaml 片段
controller:
  image:
    tag: "2.440.3-lts-jdk17"
  resources:
    requests: { cpu: "500m", memory: "2Gi" }
    limits:   { cpu: "2", memory: "4Gi" }
  JCasC:
    defaultConfig: true
    configScripts:
      welcome: |
        jenkins:
          numExecutors: 0
  persistence:
    enabled: true
    size: 50Gi
    storageClass: gp3
  ingress:
    enabled: true
    hostName: jenkins.example.com
    tls:
      - secretName: jenkins-tls
        hosts: [jenkins.example.com]

agent:
  enabled: false   # 使用 dynamic K8s agent
```

## Kubernetes Plugin 配置

Cloud 配置：
- Kubernetes URL：in-cluster
- Jenkins URL：`http://jenkins.ci.svc:8080`
- Jenkins tunnel：`jenkins-agent.ci.svc:50000`
- Pod Templates：builder、maven、docker

## RBAC

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: jenkins
  namespace: ci
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
...
```

Agent Pod 需最小 RBAC，docker build 考虑 Kaniko 替代 DinD。

## 持久化

Controller PVC 存 JENKINS_HOME；**单副本 Controller**，非 Deployment 多副本写同一 PVC。

## 升级

```bash
helm upgrade jenkins jenkins/jenkins -n ci -f values.yaml
# 先 backup PVC snapshot
```

## Checklist

- [ ] Controller replicas=1 + PVC
- [ ] JCasC 配置入 Git
- [ ] Agent Pod 有 resource limit
- [ ] 禁用 privileged（或 Kaniko）
- [ ] ingress TLS

K8s 上 Jenkins 的价值在**弹性 Agent**，不在 Controller 多副本。
