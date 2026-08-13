---
title: SGLang 在 Kubernetes 上部署入门
date: 2026-09-05 12:00:00
tags:
  - SGLang
  - Kubernetes
  - 入门
categories:
  - SGLang 新手入门
---

K8s 部署关键：**GPU 资源、模型 PVC、长启动探针、Service**。

## Deployment 示意

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sglang
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sglang
  template:
    metadata:
      labels:
        app: sglang
    spec:
      containers:
        - name: sglang
          image: lmsysorg/sglang:v0.4.0
          args:
            - python
            - -m
            - sglang.launch_server
            - --model-path
            - /models/Qwen2.5-7B-Instruct
            - --host
            - 0.0.0.0
            - --port
            - "30000"
          ports:
            - containerPort: 30000
          resources:
            limits:
              nvidia.com/gpu: "1"
          volumeMounts:
            - name: models
              mountPath: /models
              readOnly: true
          readinessProbe:
            httpGet:
              path: /v1/models
              port: 30000
            initialDelaySeconds: 120
            periodSeconds: 10
      volumes:
        - name: models
          persistentVolumeClaim:
            claimName: llm-models
```

## 实践建议

| 项 | 建议 |
|----|------|
| 模型 | PVC/本地盘预热 |
| TP | 多卡时 `nvidia.com/gpu` 与 `--tp-size` 一致 |
| 探针 | 给足加载时间 |
| 入口 | Ingress + 鉴权限流 |
| 小模型 | 可多副本；大模型 TP 通常单副本 |

## 反模式

- 无 GPU limit 调度到 CPU 节点
- readiness 过短导致 CrashLoop
- 每次 Pod 启动都在线拉模型

下一篇：**监控**。
