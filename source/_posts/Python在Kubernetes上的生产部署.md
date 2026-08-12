---
title: Python 在 Kubernetes 上的生产部署
date: 2026-08-22 10:45:00
tags:
  - Python
  - Kubernetes
categories:
  - Python 生产环境
---

K8s 为 Python 服务提供弹性伸缩、滚动发布与自愈能力。

## Deployment 示例

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp-api
  template:
    metadata:
      labels:
        app: myapp-api
    spec:
      containers:
        - name: api
          image: registry.example.com/myapp:1.2.3
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: myapp-secrets
            - configMapRef:
                name: myapp-config
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
```

## HPA 自动扩缩

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## Celery Worker Deployment

```yaml
# 独立 Deployment，无 Service
containers:
  - name: worker
    image: registry.example.com/myapp:1.2.3
    command: ["celery", "-A", "myapp.tasks", "worker", "-l", "info", "-c", "4"]
```

## ConfigMap + Secret

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myapp-config
data:
  LOG_LEVEL: "INFO"
  CORS_ORIGINS: "https://app.example.com"
```

## 滚动发布

```bash
kubectl set image deployment/myapp-api api=registry.example.com/myapp:1.2.4
kubectl rollout status deployment/myapp-api
kubectl rollout undo deployment/myapp-api   # 回滚
```

## Checklist

- [ ] requests/limits 已设
- [ ] liveness + readiness
- [ ] 非 root 容器用户
- [ ] PDB minAvailable ≥ 1
- [ ] 镜像 tag 不用 latest

K8s 部署与 **Prometheus 监控、CI/CD** 联动是生产标配。
