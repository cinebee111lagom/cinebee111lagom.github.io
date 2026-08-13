---
title: vLLM 在 Kubernetes 上的 SRE 部署
date: 2026-09-04 11:45:00
tags:
  - vLLM
  - SRE
  - Kubernetes
categories:
  - vLLM SRE
---

K8s 生产部署关注 **GPU 调度、模型卷、探针、资源与中断**。

## 清单

| 项 | 要求 |
|----|------|
| Device Plugin | `nvidia.com/gpu` 可分配 |
| 模型存储 | PVC/本地盘预热，只读挂载 |
| 镜像 | 内网仓 + digest |
| Secret | API key、HF token（若需） |
| 节点 | GPU taint/label，CPU 任务勿占 |

## 关键字段

```yaml
resources:
  limits:
    nvidia.com/gpu: "1"
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 120
  periodSeconds: 10
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 15"]  # 给 LB 摘流
```

TP=4 时：`nvidia.com/gpu: "4"`，并 `nodeSelector`/affinity 绑合同一节点（本机 TP）。

## PDB 与滚动

```yaml
minAvailable: 1   # 多副本小模型
```

大模型单副本：升级用 **蓝绿/备池**，勿裸 rolling 中断。

## 故障

| 现象 | 查 |
|------|----|
| Pending | GPU 库存、taint |
| CrashLoop | OOM、shm、参数 |
| 长时间未 Ready | 模型加载、PVC |

## 反模式

- emptydir 放模型每次拉 HF
- 探针过短杀加载中容器
- 多卡 TP 跨节点硬调度

K8s 上线门禁：**测试 Pod 推理成功 + metrics 可刮**。
