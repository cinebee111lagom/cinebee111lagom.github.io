---
title: Volcano 架构与核心组件详解
date: 2026-08-12 15:30:00
tags:
  - Volcano
  - Kubernetes
categories:
  - Volcano
---

Volcano 在 Kubernetes 之上扩展了调度能力，核心由**调度器、控制器、Webhook** 和一组 **CRD** 组成。

## 整体架构

```
用户提交 Volcano Job
       ↓
  vc-controller-manager（创建 Pod、维护状态）
       ↓
  vc-scheduler（批调度决策，替代/增强 kube-scheduler）
       ↓
  kubelet 启动 Pod
```

## 核心组件

### vc-scheduler

Volcano 调度器，负责：

- 过滤（Filter）：节点资源、亲和性、GPU 数量
- 打分（Score）：负载均衡、数据本地性
- **Bind**：将 Pod 绑定到节点
- **Gang**：检查 PodGroup minAvailable

可通过 `--scheduler-name=volcano` 让 Job 只走 Volcano 调度。

### vc-controller-manager

控制器管理 Volcano CRD 生命周期：

- Job 状态机（Pending → Running → Completed / Failed）
- PodGroup 与 Pod 关联
- Queue 资源统计

### vc-webhook-manager

准入 Webhook，校验 Job、PodGroup、Queue 等资源的合法性。

## 核心 CRD

| CRD | 作用 |
|-----|------|
| **Job** | 批作业，含 tasks、policies、minAvailable |
| **PodGroup** | 逻辑 Pod 组，Gang Scheduling 单元 |
| **Queue** | 资源队列，capability + deserved |
| **VcJob** / **Job** | 用户面向的批任务定义 |

## 与 kube-scheduler 共存

同一集群可运行两个调度器：

- 普通 Deployment → `schedulerName: default-scheduler`
- 批任务 → `schedulerName: volcano`

Volcano 只处理显式指定或带 Volcano 注解的 Pod。

## 小结

Volcano 不是替换 Kubernetes，而是在其上调度层做**批处理增强**。理解组件分工，是后续配置 Queue、Job 的基础。
