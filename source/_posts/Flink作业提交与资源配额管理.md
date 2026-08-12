---
title: Flink 作业提交与资源配额管理
date: 2026-08-18 12:15:00
tags:
  - Flink
  - 资源管理
categories:
  - Flink SRE
---

多团队共享 Flink 集群时，资源配额与提交规范是 SRE 治理重点。

## Application vs Session

| | Application | Session |
|---|-------------|---------|
| 隔离 | 强 | 弱 |
| 资源 | 独立 TM 池 | 共享 |
| 生产 | **推荐** | 不推荐多团队 |

## YARN 队列配额

```bash
flink run-application -t yarn-application \
  -Dyarn.application.queue=realtime-prod \
  -Dtaskmanager.memory.process.size=8192m \
  -Dtaskmanager.numberOfTaskSlots=4 \
  -Dyarn.application.node-label=ssd \
  ...
```

## K8s ResourceQuota

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: flink-realtime
  namespace: flink-prod
spec:
  hard:
    requests.cpu: "64"
    requests.memory: 256Gi
    limits.cpu: "128"
    limits.memory: 512Gi
    pods: "50"
```

## 作业命名与标签

```yaml
-Dyarn.application.name=team-orders-v3
-Dmetrics.scope.operator=orders-v3
```

K8s：`labels: team=payment, env=prod, cost-center=cc123`

## 提交规范

| 规则 | 说明 |
|------|------|
| jar 版本化 | `orders-job-1.2.3.jar` 存 S3 |
| 并行度上限 | 需审批 > 128 |
| 状态评估 | 新作业 > 50GB state 需架构评审 |
| Git 关联 | CI 构建 jar，禁止手工 scp |

## Slot 共享

```yaml
cluster.evenly-spread-out-slots: true
```

避免单 TM 堆叠过多 subtask。

## 多租户隔离

- 团队独立 Namespace + Quota
- 独立 Checkpoint 前缀 `s3://bucket/team-a/`
- 网络 Policy 限制 TM  egress

## 检查清单

- [ ] 生产禁止 Session 随意提交
- [ ] Queue/Quota 已配置
- [ ] 作业清单与 owner 可查询
- [ ] 僵尸作业定期清理
- [ ] 资源使用率月度 review

资源治理防止**一个作业拖垮全集群**。
