---
title: SGLang 在 Kubernetes 上的 SRE 部署
date: 2026-09-06 10:45:00
tags:
  - SGLang
  - SRE
  - Kubernetes
categories:
  - SGLang SRE
---

K8s 上跑 SGLang，关键是 **GPU 调度、模型卷、探活与优雅退出**。

## 资源清单

| 资源 | 要点 |
|------|------|
| Deployment/StatefulSet | GPU limits、nodeSelector/affinity |
| Service | ClusterIP / 接入网关 |
| PVC / HostPath / 本地盘 | 模型权重 |
| ConfigMap/Secret | 启动参数、API Key |
| HPA/自定义扩缩 | 按队列或 QPS（谨慎） |
| PDB | 避免同时抽空副本 |

## 探活建议

| 探针 | 建议 |
|------|------|
| startupProbe | 模型加载可能很长，超时放宽 |
| readiness | 能接请求再进 LB |
| liveness | 避免误杀「慢但健康」实例 |

## 调度

- 使用 NVIDIA device plugin / GPU Operator  
- TP 多卡：同一节点、拓扑感知（按集群能力）  
- 污点与容忍：专用 GPU 节点池  

## 运维注意

- 滚动时关注 **缓存冷启动** 对 TTFT 的冲击  
- 日志与 metrics 端口纳入 NetworkPolicy 例外策略  
- 优雅终止：给足 `terminationGracePeriodSeconds` 排空请求  

## 反模式

- readiness 过严导致永远 Ready=False  
- 模型放空 PVC 每次冷下载  
- 多卡 Pod 被调度到不同节点

**清单化：镜像、卡型、挂载路径、探活超时、资源 request/limit。**
