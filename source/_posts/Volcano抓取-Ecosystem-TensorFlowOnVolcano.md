---
title: Volcano 抓取：TensorFlow on Volcano
date: 2026-09-14 09:59:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/Ecosystem/TensorFlowOnVolcano>

---

### TensorFlow简介

TensorFlow是一个基于数据流编程的符号数学系统，被广泛应用于各类机器学习算法的编程实现，其前身是谷歌的神经网络算法库DistBelief。

### TensorFlow on Volcano

PS-worker模型：Parameter Server执行模型相关业务，Work Server训练相关业务，推理计算、梯度计算等[1]。

TensorFlow on Kubernetes存在诸多的问题

资源隔离

缺乏GPU调度、Gang schduler。

进程遗留问题

训练日志保存不方便

创建tftest.yaml

```
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
name: tensorflow-dist-mnist
spec:
minAvailable: 3
schedulerName: volcano
plugins:
env: []
svc: []
policies:
- event: PodEvicted
action: RestartJob
queue: default
tasks:
- replicas: 1
name: ps
template:
spec:
containers:
- command:
- sh
- -c
- |
PS_HOST=`cat /etc/volcano/ps.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
WORKER_HOST=`cat /etc/volcano/worker.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
export TF_CONFIG={\"cluster\":{\"ps\":[${PS_HOST}],\"worker\":[${WORKER_HOST}]},\"task\":{\"type\":\"ps\",\"index\":${VK_TASK_INDEX}},\"environment\":\"cloud\"};
python /var/tf_dist_mnist/dist_mnist.py
image: volcanosh/dist-mnist-tf-example:0.0.1
name: tensorflow
ports:
- containerPort: 2222
name: tfjob-port
resources: {}
restartPolicy: Never
- replicas: 2
name: worker
policies:
- event: TaskCompleted
action: CompleteJob
template:
spec:
containers:
- command:
- sh
- -c
- |
PS_HOST=`cat /etc/volcano/ps.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
WORKER_HOST=`cat /etc/volcano/worker.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
export TF_CONFIG={\"cluster\":{\"ps\":[${PS_HOST}],\"worker\":[${WORKER_HOST}]},\"task\":{\"type\":\"worker\",\"index\":${VK_TASK_INDEX}},\"environment\":\"cloud\"};
python /var/tf_dist_mnist/dist_mnist.py
image: volcanosh/dist-mnist-tf-example:0.0.1
name: tensorflow
ports:
- containerPort: 2222
name: tfjob-port
resources: {}
restartPolicy: Never
```

部署tftest.yaml

```
kubectl apply -f tftest.yaml
```

查看作业运行情况

```
kubectl get pod
```

---

> 完整与最新内容以官方文档为准：[TensorFlow on Volcano](https://volcano.sh/zh-Hans/docs/Ecosystem/TensorFlowOnVolcano)
