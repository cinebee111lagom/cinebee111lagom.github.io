---
title: vLLM 生产部署架构选型指南
date: 2026-09-04 09:15:00
tags:
  - vLLM
  - SRE
  - 架构
categories:
  - vLLM SRE
---

推理架构先定 **模型大小、QPS、延迟**，再选拓扑。

## 模式对比

| 模式 | 说明 | 适用 |
|------|------|------|
| 单卡单实例 | 最简单 | 7B/14B、中低 QPS |
| 多副本 + LB | 水平扩展 | 小模型高并发 |
| Tensor Parallel | 一模型切多卡 | 32B/70B |
| 多模型池 | 多 Deployment | 多业务/多尺寸 |
| 边缘单机 | Docker 固定机 | POC、专线节点 |

## 决策树

```
模型能否单卡放下？
  ├─ 是 → 副本数 = ceil(峰值QPS / 单卡QPS)
  └─ 否 → TP = 2/4/8，通常单副本多卡
要多模型？
  └─ 是 → 分池 + 网关按 model 路由
```

## 组件清单

```
Client → API Gateway（鉴权/限流）
      → vLLM Service(s)
      → GPU 节点 + 模型 PVC/本地盘
      → Prometheus + Grafana
```

## 容量粗算

| 输入 | 输出 |
|------|------|
| 峰值并发会话 | max_num_seqs / 副本 |
| 平均输入/输出 token | 影响 KV 与耗时 |
| SLO TTFT | 决定能否堆高并发 |

## 反模式

- 70B 无 TP 硬上单卡
- 小模型也 TP=8 浪费通信
- 无网关把 vLLM 直暴露公网

选型文档写清：**模型清单、GPU 型号、SLA、副本策略**。
