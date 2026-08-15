---
title: KEDA 与 Istio 集成入门
date: 2026-09-09 11:50:00
tags:
  - KEDA
  - Istio
  - 入门
categories:
  - KEDA 新手入门
---

在强制 mTLS 的网格里，KEDA 组件互相发现可能失败。可不关 sidecar，用 **端口排除注解** 作为可行方案（KEDA 组件间仍用自有 mTLS，同时经 sidecar 访问网格内 Prometheus 等）。

## 要求

Istio ≥ 1.18，集群已装 KEDA。

## Helm values 示例

```yaml
podAnnotations:
  keda:
    traffic.sidecar.istio.io/excludeInboundPorts: "9666"
    traffic.sidecar.istio.io/excludeOutboundPorts: "9443,6443"
  metricsAdapter:
    traffic.sidecar.istio.io/excludeInboundPorts: "6443"
    traffic.sidecar.istio.io/excludeOutboundPorts: "9666,9443"
  webhooks:
    traffic.sidecar.istio.io/excludeInboundPorts: "9443"
    traffic.sidecar.istio.io/excludeOutboundPorts: "9666,6443"
```

按实际监听端口核对后滚动发布，再验证组件通信与伸缩。

> 官方文档（v2.20）：[Istio](https://keda.sh/docs/2.20/integrations/istio-integration/)

