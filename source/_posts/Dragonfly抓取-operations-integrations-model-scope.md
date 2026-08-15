---
title: Dragonfly 抓取：ModelScope
date: 2026-09-14 09:27:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/integrations/model-scope/>

---

This document will help you experience how to use dragonfly with model scope.
During the downloading of datasets or models, the file size is large and
there are many services downloading the files at the same time.
The bandwidth of the storage will reach the limit and the download will be slow. Dragonfly can be
used to eliminate the bandwidth limit of the storage through P2P technology, thereby accelerating file downloading.

## Prerequisites

## Dragonfly Kubernetes Cluster Setup

For detailed installation documentation based on kubernetes cluster, please refer to
Lightweight Deployment
.

### Setup kubernetes cluster

Kind
is recommended if no Kubernetes cluster is available for testing.

Create kind multi-node cluster configuration file
kind-config.yaml
, configuration content is as follows:

```
kind
:
Cluster
apiVersion
:
kind.x
-
k8s.io/v1alpha4
nodes
:
-
role
:
control
-
plane
-
role
:
worker
extraPortMappings
:
-
containerPort
:
30950
hostPort
:
4001
-
role
:
worker
```

Create a kind multi-node cluster using the configuration file:

```
kind create cluster --config kind-config.yaml
```

Switch the context of kubectl to kind cluster:

```
kubectl config use-context kind-kind
```

### Kind loads Dragonfly image

Pull Dragonfly latest images:

```
docker pull dragonflyoss/scheduler:latest
docker pull dragonflyoss/client:latest
```

Kind cluster loads Dragonfly latest images:

```
kind load docker-image dragonflyoss/scheduler:latest
kind load docker-image dragonflyoss/client:latest
```

### Create Dragonfly cluster based on helm charts

Create helm charts configuration file
charts-config.yaml
, configuration content is as follows:

```
scheduler
:
image
:
repository
:
dragonflyoss/scheduler
tag
:
latest
metrics
:
enable
:
true
seedClient
:
image
:
repository
:
dragonflyoss/client
tag
:
latest
metrics
:
enable
:
true
client
:
image
:
repository
:
dragonflyoss/client
tag
:
latest
hostNetwork
:
true
metrics
:
enable
:
true
config
:
proxy
:
server
:
port
:
4001
```

Create a Dragonfly cluster using the configuration file:

```
$ helm repo add dragonfly https://dragonflyoss.github.io/helm-charts/
$ helm install --wait --create-namespace --namespace dragonfly-system dragonfly dragonfly/dragonfly -f charts-config.yaml
NAME: dragonfly
LAST DEPLOYED: Mon Jun  3 16:32:28 2024
NAMESPACE: dragonfly-system
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
1. Dragonfly is running without the manager. The scheduler and client load the dynamic
configuration from the local dynconfig.yaml file mounted as a ConfigMap, and clients
discover schedulers via the scheduler headless service:
dragonfly-scheduler.dragonfly-system.svc.cluster.local:8002
2. Get the scheduler address by running these commands:
export SCHEDULER_POD_NAME=$(kubectl get pods --namespace dragonfly-system -l "app=dragonfly,release=dragonfly,component=scheduler" -o jsonpath={.items[0].metadata.name})
export SCHEDULER_CONTAINER_PORT=$(kubectl get pod --namespace dragonfly-system $SCHEDULER_POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
kubectl --namespace dragonfly-system port-forward $SCHEDULER_POD_NAME 8002:$SCHEDULER_CONTAINER_PORT
echo "Visit http://127.0.0.1:8002 to use your scheduler"
3. Configure runtime to use dragonfly:
https://d7y.io/docs/getting-started/quick-start/kubernetes/
```

Check that Dragonfly is deployed successfully:

```
$ kubectl get po -n dragonfly-system
NAME                                 READY   STATUS    RESTARTS       AGE
dragonfly-client-6jgzn               1/1     Running   0             21m
dragonfly-client-qzcz9               1/1     Running   0             21m
dragonfly-scheduler-0                1/1     Running   0             21m
dragonfly-scheduler-1                1/1     Running   0             21m
dragonfly-scheduler-2                1/1     Running   0             21m
dragonfly-seed-client-0              1/1     Running   2 (21m ago)   21m
dragonfly-seed-client-1              1/1     Running   0             21m
dragonfly-seed-client-2              1/1     Running   0             21m
```

Create peer service configuration file
peer-service-config.yaml
, configuration content is as follows:

```
apiVersion
:
v1
kind
:
Service
metadata
:
name
:
peer
namespace
:
dragonfly
-
system
spec
:
type
:
NodePort
ports
:
-
name
:
http
-
4001
nodePort
:
30950
port
:
4001
selector
:
app
:
dragonfly
component
:
client
release
:
dragonfly
```

Create a peer service using the configuration file:

```
kubectl apply -f peer-service-config.yaml
```

## Use dfget to download files with
modelscope://
protocol

Note: To use dfget inside an inference container, you must install dfget and transfer file content from dfdaemon's Unix
domain socket. For details, refer to
Download in Container
.

Dragonfly's
dfget
command natively supports the
modelscope://
protocol, enabling direct P2P downloads from
ModelScope Hub without any proxy configuration. This is the simplest way to download models and datasets
with Dragonfly acceleration.

### URL Format

The
modelscope://
URL format is:

```
modelscope://[<repo_type>/]<owner>/<repo>[/<path>]
```

repo_type
(optional):
datasets
,
spaces
, or
models
(default).

owner/repo
: The repository ID (e.g.,
meta-llama/Llama-2-7b
).

path
(optional): A specific file within the repository.

revision
(optional): A branch, tag, or commit hash (defaults to
main
).

### Download a single file

```
dfget modelscope://deepseek-ai/DeepSeek-R1/config.json -O /tmp/config.json
```

### Download a single file with authentication

For private repositories or to increase rate limits, use the
--ms-token
flag:

```
dfget modelscope://deepseek-ai/DeepSeek-R1/config.json -O /tmp/config.json --ms-token=<token>
```

### Download an entire repository

Use the
--recursive
flag to download all files in a repository:

```
dfget modelscope://deepseek-ai/DeepSeek-R1 -O /tmp/DeepSeek-R1/ --recursive
```

### Download from a specific revision

Set
--ms-revision
to download from a specific branch, tag, or commit:

```
dfget modelscope://deepseek-ai/DeepSeek-R1 --ms-revision v1.0 -O /tmp/DeepSeek-R1/ --recursive
```

### Download a dataset

Prefix the URL with
datasets/
to download from a dataset repository:

```
# Download a specific file from a dataset.
dfget modelscope://datasets/rajpurkar/squad/train-v2.0.json -O /tmp/train.json
# Download an entire dataset.
dfget modelscope://datasets/rajpurkar/squad -O /tmp/squad/ --recursive
```

---

> 完整与最新内容以官方文档为准：[ModelScope](https://d7y.io/docs/next/operations/integrations/model-scope/)
