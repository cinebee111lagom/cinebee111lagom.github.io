---
title: Argo CD 版本升级与滚动迁移 SRE 流程
date: 2026-08-27 11:30:00
tags:
  - ArgoCD
  - SRE
  - 升级
categories:
  - ArgoCD SRE
---

Argo CD 升级影响全组织交付，必须 **staging 验证 + 滚动 + 回滚方案**。

## 升级前

- [ ] 阅读 [Release Notes](https://github.com/argoproj/argo-cd/releases) Breaking Changes
- [ ] staging 集群同版本跳跃演练
- [ ] 备份 argocd-secret + Application CR
- [ ] 通知平台：维护窗口

## Helm 升级

```bash
helm repo update
helm search repo argo/argo-cd --versions | head

# staging
helm upgrade argocd argo/argo-cd -n argocd \
  --version 7.0.0 \
  -f values-staging.yaml \
  --wait

# 验收
argocd version
argocd app list
argocd app sync test-app --dry-run
```

staging 观察 24~72h → prod 同样操作。

## CRD 变更注意

Major 版本可能更新 CRD，Helm 需：

```bash
helm upgrade argocd argo/argo-cd -n argocd --skip-crds  # 或先 apply crd
kubectl apply -k https://github.com/argoproj/argo-cd/manifests/crds?ref=v2.11.0
```

## 回滚

```bash
helm rollback argocd -n argocd
# 或 pin 上一 chart version 重新 upgrade
```

验证 UI、Sync、SSO 登录。

## 兼容性矩阵

| 项 | 检查 |
|----|------|
| K8s 版本 | Argo CD 官方 compatibility |
| Redis HA chart | subchart 版本 |
| Dex/OIDC | 配置格式是否变 |
| CLI | 与 server 同 minor 版本 |

## 反模式

- 跨多个 major 一次跳
- prod 首个升级无 staging
- 升级窗口内合并大量应用 Manifest 变更

升级 Runbook 归档：**版本号、时间、问题、回滚是否触发**。
