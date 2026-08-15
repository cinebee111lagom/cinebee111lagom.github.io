---
title: Volcano 抓取：MindSpore on Volcano
date: 2026-09-14 10:01:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/Ecosystem/MindSporeOnVolcano>

---

### Mindspore简介

MindSpore是华为公司推出的新一代深度学习框架，是源于全产业的最佳实践，最佳匹配昇腾处理器算力，支持终端、边缘、云全场景灵活部署，开创全新的AI编程范式，降低AI开发门槛。

### MindSpore on volcano

在集群中新建mindspore-cpu.yaml如下

```
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
name: mindspore-cpu
spec:
minAvailable: 1
schedulerName: volcano
policies:
- event: PodEvicted
action: RestartJob
plugins:
ssh: []
env: []
svc: []
maxRetry: 5
queue: default
tasks:
- replicas: 8
name: "pod"
template:
spec:
containers:
- command: ["/bin/bash", "-c", "python /tmp/lenet.py"]
image: lyd911/mindspore-cpu-example:0.2.0
imagePullPolicy: IfNotPresent
name: mindspore-cpu-job
resources:
limits:
cpu: "1"
requests:
cpu: "1"
restartPolicy: OnFailure
```

进行部署。

```
kubectl apply -f mindspore-cpu.yaml
```

查询集群下作业运行情况。

```
kubectl get pods
```

---

> 完整与最新内容以官方文档为准：[MindSpore on Volcano](https://volcano.sh/zh-Hans/docs/Ecosystem/MindSporeOnVolcano)
