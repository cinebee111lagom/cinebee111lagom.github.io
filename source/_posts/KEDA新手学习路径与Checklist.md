---
title: KEDA 新手学习路径与 Checklist
date: 2026-09-09 12:10:00
tags:
  - KEDA
  - Checklist
  - 入门
categories:
  - KEDA 新手入门
---

## 学习顺序

1. 概念与架构 → CRD → 认证  
2. Helm 部署 → Hello 示例  
3. 选一个业务 scaler 配 ScaledObject  
4. 接 Prometheus 看板  
5. 读排查与迁移（升级前）  
6. 若有服务网格，再读 Istio 集成  

## 上线 Checklist

- [ ] K8s ≥ 1.30，三组件 Ready
- [ ] apiservice external.metrics 为 True
- [ ] webhook 9443 / metrics 6443 网络通
- [ ] 鉴权用 TriggerAuthentication，无明文连接串进 Git
- [ ] 压测验证 0↔1 与 1↔N
- [ ] 错误与 scaler 延迟告警已配
- [ ] 回滚：保留上一 chart 版本与 ScaledObject 清单

> 官方文档（v2.20）：[Docs home](https://keda.sh/docs/2.20/)

