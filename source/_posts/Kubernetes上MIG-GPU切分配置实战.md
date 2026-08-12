---
title: Kubernetes 上 MIG GPU 切分配置实战
date: 2026-08-13 11:30:00
tags:
  - GPU切分
  - MIG
  - Kubernetes
categories:
  - GPU切分
---

在 K8s 中使用 MIG，需要 **GPU Operator + MIG Manager + Device Plugin** 协同，将 MIG 实例暴露为可调度资源。

## 架构

```
节点启用 MIG → MIG Manager 配置 profile
            → Device Plugin 注册 nvidia.com/mig-1g.10gb 等
            → Pod 请求 limits: nvidia.com/mig-1g.10gb: 1
            → 容器内看到独立 GPU UUID
```

## 安装 GPU Operator

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator -n gpu-operator --create-namespace \
  --set migManager.enabled=true
```

## 节点 MIG 策略

```yaml
# ConfigMap: mig-parted-config
apiVersion: v1
kind: ConfigMap
metadata:
  name: mig-parted-config
  namespace: gpu-operator
data:
  config.yaml: |
    - devices: all
      mig-enabled: true
      mig-devices:
        "1g.10gb": 7
```

## Pod 请求 MIG

```yaml
resources:
  limits:
    nvidia.com/mig-1g.10gb: 1
```

调度器按 MIG 实例粒度分配，一张 A100 可同时跑 7 个 Pod。

## 节点 Label

```bash
kubectl label nodes gpu-node-1 nvidia.com/mig.config=all-1g.10gb
```

MIG Manager 根据 label 自动配置 profile。

## 常见问题

| 问题 | 处理 |
|------|------|
| Pod Pending | 节点无可用 MIG 实例 |
| 看不到 MIG 资源 | Device Plugin 版本过旧 |
| Profile 变更不生效 | 需 drain 节点并重建 MIG |

K8s + MIG 是云原生**细粒度 GPU 切分**的标准落地方式。
