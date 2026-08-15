---
title: KEDA 常见问题排查入门
date: 2026-09-09 11:20:00
tags:
  - KEDA
  - 排障
  - 入门
categories:
  - KEDA 新手入门
---

## metrics API FailedDiscoveryCheck

- 查 `kubectl get apiservice v1beta1.external.metrics.k8s.io -o yaml`
- CNI/网络策略放行；托管集群可考虑 metrics-apiserver `hostNetwork`
- 代理环境把相关 ClusterIP 加入 apiserver `no_proxy`
- EKS/GKE 放行控制面到节点 **TCP 6443**

## 申请 ScaledObject 超时

常为 admission webhook **9443** 不可达：开防火墙、开 webhook debug 日志确认是否收到请求。

## 看起来不扩缩

上游 scaler 报错时默认保持当前副本（除非配置 `fallback`）。查 operator/metrics 日志与 ScaledObject READY/ACTIVE。

## 与 Istio

默认排障可能建议关 sidecar；若必须注入，用 excludeInbound/OutboundPorts 注解（见 Istio 集成文）。

> 官方文档（v2.20）：[Troubleshooting](https://keda.sh/docs/2.20/troubleshooting/)

