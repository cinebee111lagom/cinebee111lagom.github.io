---
title: Dragonfly 抓取：Triton Server
date: 2026-09-14 09:30:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/integrations/triton-server/>

---

This document will help you experience how to use Dragonfly with
TritonServe
.
During the downloading of models, the file size is large and there are many services downloading the files at the same time.
The bandwidth of the storage will reach the limit and the download will be slow.

Dragonfly can be used to eliminate the bandwidth limit of the storage through P2P technology, thereby accelerating file downloading.

## Installation

By integrating Dragonfly Repository Agent into Triton, download traffic through Dragonfly to
pull models stored in S3, OSS, GCS, and ABS, and register models in Triton. The Dragonfly Repository Agent is in
the
dragonfly-repository-agent
repository.

### Prerequisites

### Dragonfly Kubernetes Cluster Setup

For detailed installation documentation, please refer to
Lightweight Deployment
.

#### Prepare Kubernetes Cluster

Kind
is recommended if no kubernetes cluster is available for testing.

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

#### Kind loads Dragonfly image

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

#### Create Dragonfly cluster based on helm charts

Create helm charts configuration file
charts-config.yaml
and set
client.config.proxy.rules.regex
to match the download path of the object storage.
Example: add
regex:.*models.*
to match download request from object storage bucket
models
.
Configuration content is as follows:

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
registryMirror
:
addr
:
https
:
//index.docker.io
rules
:
-
regex
:
blobs/sha256.*
# Proxy all http download requests of model bucket path.
-
regex
:
.
*models.*
```

Create a Dragonfly cluster using the configuration file:

```
$ helm repo add dragonfly https://dragonflyoss.github.io/helm-charts/
$ helm install --wait --create-namespace --namespace dragonfly-system dragonfly dragonfly/dragonfly -f charts-config.yaml
LAST DEPLOYED: Mon June 27 19:56:34 2024
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
4. Get Jaeger query URL by running these commands:
export JAEGER_QUERY_PORT=$(kubectl --namespace dragonfly-system get services dragonfly-jaeger-query -o jsonpath="{.spec.ports[0].port}")
kubectl --namespace dragonfly-system port-forward service/dragonfly-jaeger-query 16686:$JAEGER_QUERY_PORT
echo "Visit http://127.0.0.1:16686/search?limit=20&lookback=1h&maxDuration&minDuration&service=dragonfly to query download events"
```

Check that Dragonfly is deployed successfully:

```
$ kubectl get pods -n dragonfly-system
NAME                                 READY   STATUS    RESTARTS       AGE
dragonfly-client-qhkn8               1/1     Running   0              21m3s
dragonfly-client-qzcz9               1/1     Running   0              21m3s
dragonfly-scheduler-0                1/1     Running   0              21m3s
dragonfly-scheduler-1                1/1     Running   0              21m3s
dragonfly-scheduler-2                1/1     Running   0              21m3s
dragonfly-seed-client-0              1/1     Running   0              21m3s
dragonfly-seed-client-1              1/1     Running   0              21m3s
dragonfly-seed-client-2              1/1     Running   0              21m3s
```

#### Expose the Proxy service port

Create the
dfstore.yaml
configuration file to expose the port on which the
Dragonfly Peer's HTTP proxy listens. The default port is
4001
and set
targetPort
to
4001
.

```
kind
:
Service
apiVersion
:
v1
metadata
:
name
:
dfstore
spec
:
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
ports
:
-
protocol
:
TCP
port
:
4001
targetPort
:
4001
type
:
NodePort
```

Create service:

```
kubectl --namespace dragonfly-system apply -f dfstore.yaml
```

Forward request to Dragonfly Peer's HTTP proxy:

```
kubectl --namespace dragonfly-system port-forward service/dfstore 4001:4001
```

### Install Dragonfly Repository Agent

#### Set Dragonfly Repository Agent configuration

Create the
dragonfly_config.json
configuration file, the configuration is as follows:

Notice: Replace the
addr
address with your actual address.

```
{
"proxy": "http://127.0.0.1:4001",
"header": {
},
"filter": [
"X-Amz-Algorithm",
"X-Amz-Credential&X-Amz-Date",
"X-Amz-Expires",
"X-Amz-SignedHeaders",
"X-Amz-Signature"
]
}
```

proxy: The address of Dragonfly Peer's HTTP Proxy.

header: Adds a request header to the request.

filter: Used to generate unique tasks and filter unnecessary query parameters in the URL.

In the filter of the configuration, set different values when using different object storage:

#### Set Model Repository configuration

Create
cloud_credential.json
cloud storage credential, the configuration is as follows:

```
{
"gs": {
"": "PATH_TO_GOOGLE_APPLICATION_CREDENTIALS",
"gs://gcs-bucket-002": "PATH_TO_GOOGLE_APPLICATION_CREDENTIALS_2"
},
"s3": {
"": {
"secret_key": "AWS_SECRET_ACCESS_KEY",
"key_id": "AWS_ACCESS_KEY_ID",
"region": "AWS_DEFAULT_REGION",
"session_token": "",
"profile": ""
},
"s3://s3-bucket-002": {
"secret_key": "AWS_SECRET_ACCESS_KEY_2",
"key_id": "AWS_ACCESS_KEY_ID_2",
"region": "AWS_DEFAULT_REGION_2",
"session_token": "AWS_SESSION_TOKEN_2",
"profile": "AWS_PROFILE_2"
}
},
"as": {
"": {
"account_str": "AZURE_STORAGE_ACCOUNT",
"account_key": "AZURE_STORAGE_KEY"
},
"as://Account-002/Container": {
"account_str": "",
"account_key": ""
}
}
}
```

In order to pull the model through Dragonfly, the model configuration file needs to
be added following code in
config.pbtxt
file:

```
model_repository_agents
{
agents [
{
name: "dragonfly",
}
]
}
```

The
densenet_onnx example
contains modified configuration and model file. Modified
config.pbtxt
such as:

```
name: "densenet_onnx"
platform: "onnxruntime_onnx"
max_batch_size : 0
input [
{
name: "data_0"
data_type: TYPE_FP32
format: FORMAT_NCHW
dims: [ 3, 224, 224 ]
reshape { shape: [ 1, 3, 224, 224 ] }
}
]
output [
{
name: "fc6_1"
data_type: TYPE_FP32
dims: [ 1000 ]
reshape { shape: [ 1, 1000, 1, 1 ] }
label_filename: "densenet_labels.txt"
}
]
model_repository_agents
{
agents [
{
name: "dragonfly",
}
]
}
```

### Triton Server integrates Dragonfly Repository Agent plugin

#### Install Triton Server with Docker

Pull
dragonflyoss/dragonfly-repository-agent
image which is integrated Dragonfly Repository Agent plugin
in Triton Server, refer to
Dockerfile
.

```
docker pull dragonflyoss/dragonfly-repository-agent:latest
```

Run the container and mount the configuration directory:

```
docker run --network host --rm \
-v ${path-to-config-dir}:/home/triton/ \
dragonflyoss/dragonfly-repository-agent:latest tritonserver \
--model-repository=${model-repository-path}
```

path-to-config-dir
: The files path of
dragonfly_config.json
&
cloud_credential.json
.

model-repository-path
: The path of remote model repository.

The correct output is as follows:


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Triton Server](https://d7y.io/docs/next/operations/integrations/triton-server/)
