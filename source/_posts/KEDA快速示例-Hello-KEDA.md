---
title: KEDA 快速示例：Hello KEDA
date: 2026-09-09 10:00:00
tags:
  - KEDA
  - 实战
  - 入门
categories:
  - KEDA 新手入门
---

官方入门：部署简单 HTTP 应用 → Service → ScaledObject（Prometheus 触发）→ 压测观察扩缩。

## 骨架

1. Deployment（如 `hashicorp/http-echo`）
2. Service 暴露
3. ScaledObject 示例触发器：

```yaml
triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus-server.default.svc:9090
      threshold: "5"
      query: sum(rate(http_requests_total[1m]))
```

4. `hey`/`curl` 打流，`kubectl get pods -w` 观察

前提：集群已装 KEDA，且 Prometheus 能刮到应用指标。结束后删除 ScaledObject/Service/Deployment。

> 官方文档（v2.20）：[Getting Started Example](https://keda.sh/docs/2.20/deploy/)

