---
title: Argo CD 与 Sealed Secrets、External Secrets 生产实践
date: 2026-08-27 12:15:00
tags:
  - ArgoCD
  - SRE
  - Secret
categories:
  - ArgoCD SRE
---

生产 GitOps 必须 **Secret 不进明文 Git**，与 Argo CD 深度集成。

## 方案选型

| 方案 | 运维复杂度 | 企业特性 |
|------|------------|----------|
| Sealed Secrets | 低 | 公钥加密进 Git |
| External Secrets | 中 | Vault/AWS SM/阿里云 KMS |
| SOPS + Age/PGP | 中 | 文件级加密 |

## Sealed Secrets + Argo CD

```yaml
# Git 中提交 SealedSecret
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: db-cred
  namespace: myapp
spec:
  encryptedData:
    password: AgBx...
```

Argo CD Sync → controller 解密 → 普通 Secret。

**注意**：SealedSecret 绑定 namespace/name，改需重新 seal。

## External Secrets

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-cred
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-prod
    kind: ClusterSecretStore
  target:
    name: db-cred
    creationPolicy: Owner
  data:
    - secretKey: password
      remoteRef:
        key: secret/data/myapp/db
        property: password
```

Argo CD 管理 ExternalSecret CR，**真实 Secret 由 operator 生成**。

```yaml
spec:
  ignoreDifferences:
    - group: ""
      kind: Secret
      name: db-cred
      jsonPointers:
        - /data
```

## Argo CD 自身 Secret

| Secret | 管理 |
|--------|------|
| repo credential | External Secrets 或 Sealed |
| cluster credential | 轮换 SA token |
| oidc clientSecret | K8s Secret 引用 |

## 密钥轮换 Runbook

1. Vault 更新 secret 版本
2. ExternalSecret refresh（或等 interval）
3. 滚动 restart 依赖该 Secret 的 Deployment
4. Argo CD 不应 OutOfSync（ignore / 只管理 CR）

## 反模式

- Sealed Secrets 私钥未备份
- ExternalSecret 与 Git 中 Secret 双写
- prod/dev 共用 Sealed Secrets 公钥

Secret 方案在 **平台 bootstrap** 阶段与 Argo CD 一并落地。
