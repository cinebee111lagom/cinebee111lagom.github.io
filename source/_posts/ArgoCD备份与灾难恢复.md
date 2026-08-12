---
title: Argo CD 备份与灾难恢复
date: 2026-08-27 11:15:00
tags:
  - ArgoCD
  - SRE
  - 备份
categories:
  - ArgoCD SRE
---

GitOps 下 **Git 是主备份**，但 Argo CD 控制面状态仍需 DR 计划。

## 需备份的数据

| 数据 | 位置 | 重要性 |
|------|------|--------|
| Git 仓库 | GitHub/GitLab | **最高**（真相来源） |
| Application CR | K8s etcd | 高（可用 Git 重建） |
| argocd-secret | K8s Secret | 高（repo/cluster 凭证） |
| argocd-cm / rbac-cm | ConfigMap | 中（应 Git 化） |
| Redis | 缓存 | 低（可重建） |

## Velero 备份

```bash
velero backup create argocd-backup \
  --include-namespaces argocd \
  --wait
```

定期 cron + 异地对象存储。

## 手动导出关键 Secret

```bash
kubectl get secret argocd-secret -n argocd -o yaml > argocd-secret-backup.yaml
kubectl get secret -n argocd -l argocd.argoproj.io/secret-type=repository -o yaml > repos-backup.yaml
kubectl get secret -n argocd -l argocd.argoproj.io/secret-type=cluster -o yaml > clusters-backup.yaml
```

**加密存储**，勿明文进 Git。

## 灾难恢复流程

```
1. 新建 Mgmt 集群
2. Helm 安装 Argo CD HA
3. 恢复 argocd-secret / repo / cluster secrets
4. 恢复或从 Git  bootstrap Application（App of Apps）
5. 验证 cluster list、repo connect
6. 批量 Refresh + Sync staging → prod
```

RTO 目标：**≤ 2 小时**（含验证）。

## App of Apps 自举

```yaml
# bootstrap 仅需一个 root Application 指向 Git clusters/prod/
# 其余 Application 由 Git 定义，重建成本低
```

## DR 演练 Checklist

- [ ] 从备份恢复至隔离集群
- [ ] 所有 repo 连接 Successful
- [ ] 所有 cluster 连接 Successful
- [ ] 抽样 10 个 prod app Synced + Healthy

## 反模式

- 仅备份 Redis 不备份 secret
- repo token 只在 Argo CD 内，Git 无镜像
- 从未做 restore 演练

**Git + Secret 备份双轨**是 GitOps DR 黄金法则。
