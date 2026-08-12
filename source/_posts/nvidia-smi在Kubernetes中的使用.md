---
title: nvidia-smi 在 Kubernetes 中的使用
date: 2026-08-24 12:45:00
tags:
  - nvidia-smi
  - Kubernetes
categories:
  - nvidia-smi 新手入门
---

K8s GPU 节点上，nvidia-smi 在**宿主机**和**Pod 内**都可使用，排查调度问题必备。

## 组件

```
GPU Node
  ├── NVIDIA Driver（宿主机）
  ├── nvidia-container-toolkit
  ├── NVIDIA Device Plugin（K8s）
  └── GPU Operator（可选，一站式）
```

## 宿主机检查

```bash
ssh gpu-node-1
nvidia-smi
kubectl get node gpu-node-1 -o json | jq '.status.capacity'
# "nvidia.com/gpu": "8"
```

## Pod 内运行 smi

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  restartPolicy: Never
  containers:
    - name: cuda
      image: nvidia/cuda:12.1.0-base-ubuntu22.04
      command: ["nvidia-smi"]
      resources:
        limits:
          nvidia.com/gpu: 1
```

```bash
kubectl apply -f gpu-test.yaml
kubectl logs gpu-test
```

## 调试 Pod（长期）

```bash
kubectl run gpu-debug --rm -it --restart=Never \
  --image=nvidia/cuda:12.1.0-base-ubuntu22.04 \
  --overrides='{"spec":{"containers":[{"name":"c","image":"nvidia/cuda:12.1.0-base-ubuntu22.04","command":["bash"],"stdin":true,"tty":true,"resources":{"limits":{"nvidia.com/gpu":"1"}}}]}}' \
  -- bash
# 容器内 nvidia-smi
```

## 常见问题排查

| 现象 | smi 排查 |
|------|----------|
| Pod Pending | 宿主机 smi 正常？资源够？ |
| 看不到 GPU | device plugin 日志 |
| 显存 OOM | 宿主机 smi 看进程 |
| MIG | smi -L 看 MIG 设备，与 resource 名匹配 |

```bash
kubectl logs -n kube-system ds/nvidia-device-plugin-daemonset
```

## 与监控关系

- **节点级**：宿主机 smi / dcgm-exporter
- **Pod 级**：平台侧聚合，smi 看宿主机 PID 反查 Pod

```bash
# 宿主机
nvidia-smi --query-compute-apps=pid,used_gpu_memory --format=csv
crictl ps | grep <pid映射>
```

K8s GPU 问题：**先看节点 smi，再看 Pod events 和 device plugin**。
