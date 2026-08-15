---
title: KEDA 配置自动伸缩流程入门
date: 2026-09-09 10:10:00
tags:
  - KEDA
  - Scaler
  - 入门
categories:
  - KEDA 新手入门
---

## 五步

1. **选 Scaler**：查官方 Scalers 列表（RabbitMQ、Cron、Prometheus、HTTP Add-on 等）
2. **安装附加组件**（若需要，如 HTTP Add-on 仍为 beta）
3. **写 ScaledObject**：`scaleTargetRef` + `triggers` + 可选 polling/cooldown/max
4. **kubectl apply** 并 `kubectl get scaledobjects`
5. **监控**：看 ScaledObject 状态与 `kubectl logs -n keda -l app=keda-operator`

READY/ACTIVE 异常时先查 trigger 鉴权与源连通性。

> 官方文档（v2.20）：[Setup Autoscaling](https://keda.sh/docs/2.20/setupscaler/)

