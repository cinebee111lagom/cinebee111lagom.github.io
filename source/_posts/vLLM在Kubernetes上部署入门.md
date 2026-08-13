---
title: vLLM 在 Kubernetes 上部署入门
date: 2026-09-03 12:15:00
tags:
  - vLLM
  - Kubernetes
  - 入门
categories:
  - vLLM 新手入门
---

K8s 上部署 vLLM 的关键是：**GPU 调度 + PVC 模型 + Service**。

## Deployment 示意

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
        - name: vllm
          image: vllm/vllm-openai:v0.6.0
          args:
            - --model
            - /models/Qwen2.5-7B-Instruct
            - --host
            - 0.0.0.0
            - --port
            - "8000"
          ports:
            - containerPort: 8000
          resources:
            limits:
              nvidia.com/gpu: 1
          volumeMounts:
            - name: models
              mountPath: /models
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 60
      volumes:
        - name: models
          persistentVolumeClaim:
            claimName: llm-models
```

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm
spec:
  selector:
    app: vllm
  ports:
    - port: 8000
      targetPort: 8000
```

## 实践建议

| 项 | 建议 |
|----|------|
| 模型 | PVC/本地盘预热，勿每次拉取 |
| GPU | 1 Pod 绑固定 GPU 数（TP） |
| 探针 | readiness 要给足启动时间 |
| HPA | 按自定义队列指标，勿盲目按 CPU |
| 入口 | Ingress + 鉴权/限流 |

## 多副本

小模型可 `replicas>1` + Service 负载均衡；大模型 TP 多卡通常 **单副本多 GPU**。

## 反模式

- 无 GPU 资源请求导致调度到 CPU 节点
- readiness 3 秒就失败重启循环
- 多个大模型 Pod 抢同一节点显存

下一篇：**指标与监控**。
