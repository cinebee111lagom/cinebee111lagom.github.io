---
title: Volcano 抓取：Volcano Job Policy 用户指南
date: 2026-09-14 09:44:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_job_policy>

---

## 背景

Policy
为 Volcano Job 与 Task 的生命周期管理提供 API。例如，在部分场景下——尤其是 AI、大数据与 HPC 领域——若任意
master
或
worker
失败，需要重新启动作业。用户可在
job.spec
下为 Volcano Job 配置
policy
即可轻松实现。

## 要点

Volcano 允许用户为 Volcano Job 或 Task 配置一对
Event
（
Events
）与
Action
。当指定的事件（events）发生时，将触发对应操作。若配置了
timeout
，则在超时延迟后执行目标操作。

若仅在
job.spec
下配置策略，默认对所有 Task 生效。若仅在
task.spec
下配置，则仅对该 Task 生效。若在 Job 与 Task 两级均配置，以 Task 级策略为准。

用户可为同一 Job 或 Task 配置多条策略。

目前 Volcano 提供
6 个内置事件
，如下所示。

目前 Volcano 提供
7 个内置操作
，如下所示。

## 示例

配置一对
event
与
action
。

```
apiVersion
:
batch.volcano.sh/v1alpha1
kind
:
Job
metadata
:
name
:
tensorflow
-
dist
-
mnist
spec
:
minAvailable
:
3
schedulerName
:
volcano
plugins
:
env
:
[
]
svc
:
[
]
policies
:
-
event
:
PodEvicted
# Job level policy. If any pod is evicted, restart the job.
action
:
RestartJob
queue
:
default
tasks
:
-
replicas
:
1
name
:
ps
template
:
spec
:
containers
:
-
command
:
-
sh
-
-
c
-
|
PS_HOST=`cat /etc/volcano/ps.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
WORKER_HOST=`cat /etc/volcano/worker.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
export TF_CONFIG={\"cluster\":{\"ps\":[${PS_HOST}],\"worker\":[${WORKER_HOST}]},\"task\":{\"type\":\"ps\",\"index\":${VK_TASK_INDEX}},\"environment\":\"cloud\"};   ## Get the index from the environment variable and configure it in the TF job.
python /var/tf_dist_mnist/dist_mnist.py
image
:
volcanosh/dist
-
mnist
-
tf
-
example
:
0.0.1
name
:
tensorflow
ports
:
-
containerPort
:
2222
name
:
tfjob
-
port
resources
:
{
}
restartPolicy
:
Never
-
replicas
:
2
name
:
worker
policies
:
-
event
:
TaskCompleted
# Task level policy. If this task completes, complete the job.
action
:
CompleteJob
template
:
spec
:
containers
:
-
command
:
-
sh
-
-
c
-
|
PS_HOST=`cat /etc/volcano/ps.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
WORKER_HOST=`cat /etc/volcano/worker.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
export TF_CONFIG={\"cluster\":{\"ps\":[${PS_HOST}],\"worker\":[${WORKER_HOST}]},\"task\":{\"type\":\"worker\",\"index\":${VK_TASK_INDEX}},\"environment\":\"cloud\"};
python /var/tf_dist_mnist/dist_mnist.py
image
:
volcanosh/dist
-
mnist
-
tf
-
example
:
0.0.1
name
:
tensorflow
ports
:
-
containerPort
:
2222
name
:
tfjob
-
port
resources
:
{
}
restartPolicy
:
Never
```

配置一对
events
与
action
。

```
apiVersion
:
batch.volcano.sh/v1alpha1
kind
:
Job
metadata
:
name
:
tensorflow
-
dist
-
mnist
spec
:
minAvailable
:
3
schedulerName
:
volcano
plugins
:
env
:
[
]
svc
:
[
]
queue
:
default
tasks
:
-
replicas
:
1
name
:
ps
policies
:
-
events
:
[
PodEvicted
,
PodFailed
]
# Task level policy. If any pod is evicted or fails in this task, restart the job.
action
:
RestartJob
template
:
spec
:
containers
:
-
command
:
-
sh
-
-
c
-
|
PS_HOST=`cat /etc/volcano/ps.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
WORKER_HOST=`cat /etc/volcano/worker.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
export TF_CONFIG={\"cluster\":{\"ps\":[${PS_HOST}],\"worker\":[${WORKER_HOST}]},\"task\":{\"type\":\"ps\",\"index\":${VK_TASK_INDEX}},\"environment\":\"cloud\"};   ## Get the index from the environment variable and configure it in the TF job.
python /var/tf_dist_mnist/dist_mnist.py
image
:
volcanosh/dist
-
mnist
-
tf
-
example
:
0.0.1
name
:
tensorflow
ports
:
-
containerPort
:
2222
name
:
tfjob
-
port
resources
:
{
}
restartPolicy
:
Never
-
replicas
:
2
name
:
worker
policies
:
-
event
:
TaskCompleted
# Task level policy. If this task completes, complete the job.
action
:
CompleteJob
template
:
spec
:
containers
:
-
command
:
-
sh
-
-
c
-
|
PS_HOST=`cat /etc/volcano/ps.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
WORKER_HOST=`cat /etc/volcano/worker.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
export TF_CONFIG={\"cluster\":{\"ps\":[${PS_HOST}],\"worker\":[${WORKER_HOST}]},\"task\":{\"type\":\"worker\",\"index\":${VK_TASK_INDEX}},\"environment\":\"cloud\"};
python /var/tf_dist_mnist/dist_mnist.py
image
:
volcanosh/dist
-
mnist
-
tf
-
example
:
0.0.1
name
:
tensorflow
ports
:
-
containerPort
:
2222
name
:
tfjob
-
port
resources
:
{
}
restartPolicy
:
Never
```

配置
events
、
action
与
timeout
。

```
apiVersion
:
batch.volcano.sh/v1alpha1
kind
:
Job
metadata
:
name
:
tensorflow
-
dist
-
mnist
spec
:
minAvailable
:
3
schedulerName
:
volcano
plugins
:
env
:
[
]
svc
:
[
]
queue
:
default
tasks
:
-
replicas
:
1
name
:
ps
policies
:
-
events
:
PodFailed
# Task level policy. If any pod fails in this task, restart the pod.
action
:
RestartPod
-
events
:
PodEvicted
# Task level policy. If any pod is evicted in this task, restart the job after 10 minutes.
action
:
RestartJob
timeout
:
10m
template
:
spec
:
containers
:
-
command
:
-
sh
-
-
c
-
|
PS_HOST=`cat /etc/volcano/ps.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
WORKER_HOST=`cat /etc/volcano/worker.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
export TF_CONFIG={\"cluster\":{\"ps\":[${PS_HOST}],\"worker\":[${WORKER_HOST}]},\"task\":{\"type\":\"ps\",\"index\":${VK_TASK_INDEX}},\"environment\":\"cloud\"};   ## Get the index from the environment variable and configure it in the TF job.
python /var/tf_dist_mnist/dist_mnist.py
image
:
volcanosh/dist
-
mnist
-
tf
-
example
:
0.0.1
name
:
tensorflow
ports
:
-
containerPort
:
2222
name
:
tfjob
-
port
resources
:
{
}
restartPolicy
:
Never
-
replicas
:
2
name
:
worker
policies
:
-
event
:
TaskCompleted
# Task level policy. If this task completes, complete the job.
action
:
CompleteJob
template
:
spec
:
containers
:
-
command
:
-
sh
-
-
c
-
|
PS_HOST=`cat /etc/volcano/ps.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
WORKER_HOST=`cat /etc/volcano/worker.host | sed 's/$/&:2222/g' | sed 's/^/"/;s/$/"/' | tr "\n" ","`;
export TF_CONFIG={\"cluster\":{\"ps\":[${PS_HOST}],\"worker\":[${WORKER_HOST}]},\"task\":{\"type\":\"worker\",\"index\":${VK_TASK_INDEX}},\"environment\":\"cloud\"};
python /var/tf_dist_mnist/dist_mnist.py
image
:
volcanosh/dist
-
mnist
-
tf
-
example
:
0.0.1
name
:
tensorflow
ports
:
-
containerPort
:
2222
name
:
tfjob
-
port
resources
:
{
}
restartPolicy
:
Never
```

---

> 完整与最新内容以官方文档为准：[Volcano Job Policy 用户指南](https://volcano.sh/zh-Hans/docs/UserGuide/user_guide_how_to_use_job_policy)
