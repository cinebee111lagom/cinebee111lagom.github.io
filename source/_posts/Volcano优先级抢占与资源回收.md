---
title: Volcano 优先级、抢占与资源回收
date: 2026-08-12 18:00:00
tags:
  - Volcano
  - 优先级
categories:
  - Volcano
---

多团队共享集群时，**优先级与抢占**决定谁先跑、谁被踢——Volcano 通过 PriorityClass 与 reclaimable Queue 实现。

## PriorityClass

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
preemptionPolicy: PreemptLowerPriority
```

Job / PodGroup 引用：

```yaml
spec:
  priorityClassName: high-priority
```

高优先级 Job 在资源不足时，可**驱逐**低优先级 Pod 释放 GPU。

## 抢占流程

1. 高优 Job 提交，Gang 需要 8 GPU，当前仅 4 空闲
2. Volcano 识别可抢占的低优 Job（非关键生产、可 reclaim 的 Queue）
3. 标记低优 Pod 为 Terminating
4. 资源释放后，高优 Job 整体 Gang 调度

## Queue reclaimable

```yaml
spec:
  reclaimable: true   # 空闲资源可被其他 Queue 借用
  capability:
    nvidia.com/gpu: "16"
```

- `reclaimable: true`：该 Queue 未用满时，其他 Queue 可临时使用超出 deserved 的部分
- 当 Queue 自身 Job 增多，可回收被借用的资源

## 策略建议

| 场景 | 配置 |
|------|------|
| 在线推理 | 高 priority，reclaimable: false |
| 离线训练 | 中 priority，reclaimable: true |
| 开发调试 | 低 priority，可被抢占 |

## 风险与规避

- 抢占导致训练 checkpoint 丢失 → 训练框架开启定期 checkpoint
- 频繁抢占引发 thrashing → 合理设置 Queue weight，避免过多同优先级 Job
- 生产 Job 务必设 `preemptionPolicy: Never` 或专用 Queue

优先级是集群「交通管制」，配合 Queue 配额使用效果最佳。
