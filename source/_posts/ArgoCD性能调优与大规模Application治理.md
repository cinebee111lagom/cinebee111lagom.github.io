---
title: Argo CD 性能调优与大规模 Application 治理
date: 2026-08-27 12:30:00
tags:
  - ArgoCD
  - SRE
  - 性能
categories:
  - ArgoCD SRE
---

Application 数百上千时，**controller sharding、repo 优化** 成为 SRE 重点。

## 规模信号

| 信号 | 阈值 |
|------|------|
| Application 数 | > 300 考虑 sharding |
| Reconcile 延迟 | P99 > 5min |
| repo-server CPU | 持续 > 80% |
| Git fetch P99 | > 30s |

## Controller Sharding

```yaml
# 按 cluster 分片
controller:
  replicas: 3
  env:
    - name: ARGOCD_CONTROLLER_REPLICAS
      value: "3"
    # 每个 shard 通过 hostname hash 分担 apps
```

或使用 **ApplicationSet + 多 Argo CD 实例** 按业务域拆分。

## Repo Server 优化

```yaml
repoServer:
  replicas: 3
  env:
    - name: ARGOCD_GIT_LS_REMOTE_PARALLELISM_LIMIT
      value: "5"
    - name: ARGOCD_REPO_SERVER_PARALLELISM_LIMIT
      value: "10"
  volumes:
    - name: git-cache
      emptyDir:
        sizeLimit: 10Gi
```

## Git 仓优化

| 实践 | 效果 |
|------|------|
| 拆分 monorepo | 减少单次 clone |
| shallow clone | 降低 fetch 时间 |
| 固定 branch/tag | 避免 HEAD 解析 |
| .argocd-ignore | 跳过无关路径 |

## Reconciliation 调优

```yaml
# argocd-cm
timeout.reconciliation: 300s
```

过短增加 CPU，过长延迟发现变更。

## Application 治理

- 删除僵尸 Application（Git 目录已删仍残留）
- 统一 `syncPolicy` 模板
- prod 必须归属 production Project
- 定期 audit：`OutOfSync > 7d` 清单

```bash
argocd app list -o wide | grep OutOfSync
```

## 反模式

- 单 controller 扛 1000+ app
- 超大 Helm chart 无拆分
- 每 app 独立 Git repo 导致 credential 爆炸

性能基线：**每增加 100 Application，做一次 reconcile 延迟压测**。
