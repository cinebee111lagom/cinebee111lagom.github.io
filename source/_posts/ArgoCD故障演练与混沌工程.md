---
title: Argo CD 故障演练与混沌工程
date: 2026-08-27 13:00:00
tags:
  - ArgoCD
  - SRE
  - 混沌工程
categories:
  - ArgoCD SRE
---

GitOps 控制面故障会阻塞全部发布，需 **定期演练** 验证 HA 与 Runbook。

## 演练场景

| 场景 | 方法 | 验证 |
|------|------|------|
| server pod 故障 | delete pod | UI 30s 内恢复 |
| controller 故障 | delete controller | Reconcile 恢复 |
| repo-server 故障 | delete pod | Sync 仍成功 |
| Redis 故障 | scale redis 0→1 | 告警 + 恢复 |
| Git 不可用 | 阻断 egress | Sync Failed 告警 |
| cluster 断连 | 改 network policy | ClusterDisconnected 告警 |

## 业务影响演练（staging）

```
1. 部署测试 Application
2. 删除 controller 5 分钟
3. 恢复后 Git 变更是否被 reconcile
4. prod 误 Sync 回滚演练（Git revert）
```

## 演练脚本示例

```bash
#!/bin/bash
# argocd-chaos-staging.sh
set -euo pipefail

echo "=== Pre-check ==="
argocd app list | head

echo "=== Kill repo-server ==="
kubectl delete pod -n argocd -l app.kubernetes.io/name=argocd-repo-server --wait=false
sleep 60

echo "=== Sync test app ==="
argocd app sync chaos-test --timeout 120 || echo "EXPECTED FAIL if git blocked"

echo "=== Wait recovery ==="
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=argocd-repo-server -n argocd --timeout=300s
argocd app sync chaos-test --timeout 120
```

## 成功标准

- P0 告警 ≤ 5 分钟触达
- 值班按 Runbook 完成，无未文档化即兴操作
- RTO 符合 SLA（控制面 ≤ 30min）
- DR restore 演练季度一次

## 频率

| 演练 | 周期 |
|------|------|
| Pod 故障 | 月度（staging） |
| Git/Cluster 断连 | 季度 |
| 全量 DR restore | 半年 |

## 反模式

- 仅测 HA 不测 Sync 失败告警
- prod 直接混沌无审批
- 演练不更新 Runbook

演练报告归档：**日期、场景、RTO、改进项**。
