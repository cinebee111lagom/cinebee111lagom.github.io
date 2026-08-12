---
title: Volcano 生产环境监控与运维实践
date: 2026-08-12 19:30:00
tags:
  - Volcano
  - 运维
categories:
  - Volcano
---

Volcano 上生产后，监控与运维决定集群能否长期稳定承载 AI 负载。

## 关键指标

### Job 维度

- Job Phase：`Pending` / `Running` / `Completed` / `Failed` / `Terminated`
- Job 排队时长（submit → running）
- Task 失败率与 `maxRetry` 触发次数

### Queue 维度

- `allocated` vs `capability`（各资源类型）
- Pending Job 数量 per Queue
- 是否长期打满 capability

### 调度维度

- PodGroup unschedulable 事件
- 抢占次数（preemption）
- Gang 等待时长（minAvailable 未满足时间）

## Prometheus 集成

Volcano 组件暴露 metrics 端点，可配合 ServiceMonitor 抓取：

```yaml
# volcano-scheduler metrics 默认 :8080/metrics
# volcano-controllers metrics 默认 :8081/metrics
```

常用 PromQL 思路：

```promql
# Queue 中 Pending Job 数（需根据实际 metric 名调整）
volcano_queue_pending_jobs{queue="gpu-train"}

# 调度失败计数
rate(volcano_scheduler_schedule_attempts_total{result="error"}[5m])
```

## 告警规则示例

| 告警 | 条件 | 含义 |
|------|------|------|
| QueueFull | allocated/capability > 0.95 持续 30m | 队列长期满载 |
| JobStuckPending | Pending > 2h | Gang 无法满足或资源不足 |
| SchedulerDown | volcano-scheduler 无心跳 | 批调度停摆 |

## 日志排查

```bash
kubectl logs -n volcano-system -l app=volcano-scheduler --tail=100
kubectl describe podgroup <name>
kubectl describe vcjob <name>
```

关注 Events 中的 `Unschedulable`、`Insufficient nvidia.com/gpu`。

## 运维最佳实践

1. **Queue capability ≤ 集群实际容量**，预留 10% 给系统 Pod
2. **训练 Job 设置 ttlSecondsAfterFinished**，避免 Completed Pod 堆积
3. **定期演练抢占**：验证高优 Job 能否在 SLA 内获得资源
4. **版本升级**：先在 staging 集群验证 CRD 兼容性
5. **与 Cluster Autoscaler 配合**：Gang Pending 触发节点扩容

## 故障手册

| 症状 | 可能原因 | 处理 |
|------|----------|------|
| 全部 Job Pending | scheduler 挂掉 | 重启 volcano-scheduler |
| 单 Job 永久 Pending | minAvailable > 可用 GPU | 降 replicas 或扩节点 |
| 频繁 RestartJob | 节点不稳定 / OOM | 查节点与显存 |

---

以上十篇覆盖 Volcano 从入门、架构、Gang/Queue/Job、GPU 调度到安装运维的全链路。建议阅读顺序：入门 → 架构 → PodGroup → Queue → Job → GPU → 优先级 → 对比 → 安装 → 运维。
