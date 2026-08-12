---
title: Argo CD 与 Kubernetes Secret 管理入门
date: 2026-08-26 12:15:00
tags:
  - ArgoCD
  - Secret
  - 入门
categories:
  - ArgoCD 新手入门
---

**明文 Secret 不能进 Git**，GitOps 需配套 Secret 方案。

## 方案对比

| 方案 | 原理 | 适用 |
|------|------|------|
| Sealed Secrets | 加密 Secret 可进 Git | 中小团队 |
| External Secrets | 从 Vault/AWS SM 拉取 | 企业 |
| SOPS | Mozilla 加密 YAML | 多格式 |
| argocd-secret 手动 | 集群外管理 | 临时 |

## Sealed Secrets 流程

```bash
# 集群安装 controller
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system

# 本地 kubeseal 加密
kubectl create secret generic db-cred \
  --from-literal=password=xxx --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-db-cred.yaml

# Git 提交 sealed-db-cred.yaml（加密态）
git add sealed-db-cred.yaml && git commit && git push
```

Argo CD Sync 后 controller 解密为普通 Secret。

## External Secrets 示例

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-cred
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: db-cred
  data:
    - secretKey: password
      remoteRef:
        key: database/prod
        property: password
```

ExternalSecret 可进 Git，真实密码在 Vault。

## Argo CD 自身凭证

```bash
# Git 仓凭证存在 argocd namespace Secret
argocd repo add https://github.com/private/repo.git \
  --username git --password $GITHUB_TOKEN

# 集群凭证
argocd cluster add my-context
```

## ignoreDifferences（Secret 数据）

若 Secret 由外部 controller 管理 data 字段：

```yaml
spec:
  ignoreDifferences:
    - group: ""
      kind: Secret
      jsonPointers:
        - /data
```

## 反模式

- base64 明文 Secret 进 Git
- Sealed Secrets 私钥未备份
- External Secrets 与 Git 中 Secret 双写冲突

Secret 方案应在 **平台搭建阶段** 与 Argo CD 一并确定。
