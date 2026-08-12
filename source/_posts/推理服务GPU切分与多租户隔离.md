---
title: 推理服务的 GPU 切分与多租户隔离
date: 2026-08-13 12:30:00
tags:
  - GPU切分
  - 推理
  - 多租户
categories:
  - GPU切分
---

在线推理平台常需在一卡上托管**多个模型**服务不同租户，GPU 切分是控制成本与 SLA 的关键。

## 租户需求差异

| 租户 | 模型 | 显存 | QPS | SLA |
|------|------|------|-----|-----|
| A | BERT-base | 2 GB | 高 | P99 < 50ms |
| B | LLM-7B | 16 GB | 低 | P99 < 200ms |
| C | 图像分类 | 1 GB | 中 | P99 < 30ms |

## MIG Profile 映射

```
A100 80GB → 3 × 2g.20gb + 1 × 1g.10gb（示例）
  ├── 2g → 租户 B（LLM）
  ├── 2g → 预留 / 大模型 B 副本
  ├── 2g → 弹性租户
  └── 1g → 租户 A + C 需拆到不同卡或 MPS
```

小模型优先 `1g.10gb`，7B 级模型用 `2g.20gb` 或 `3g.40gb`。

## Triton / vLLM 部署

```yaml
# 每个 MIG 实例一个 Inference Server Pod
resources:
  limits:
    nvidia.com/mig-2g.20gb: 1
```

**一实例一 Pod**，避免 MPS 混部导致显存互相挤压。

## 弹性与缩容

- 低峰：合并租户到更少 MIG 实例，释放节点
- 高峰：HPA 基于 QPS 扩容 Pod，受 MIG 实例数上限约束
- 新租户 onboarding：分配空闲 MIG profile

## 计费模型

按 MIG profile 计费（如「2g.20gb 小时单价」），比整卡计费更贴近实际消耗，利于 SaaS 定价。

推理多租户是 MIG 切分的**主战场**，隔离 + 利用率双收。
