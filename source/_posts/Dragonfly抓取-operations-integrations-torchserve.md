---
title: Dragonfly 抓取：TorchServe
date: 2026-09-14 09:29:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/integrations/torchserve/>

---

This document will help you experience how to use Dragonfly with
TorchServe
.
During the downloading of models, the file size is large and there are many services downloading the files at the same time.
The bandwidth of the storage will reach the limit and the download will be slow.

Dragonfly can be used to eliminate the bandwidth limit of the storage through P2P technology, thereby accelerating file downloading.

## Architecture

Dragonfly Endpoint
plugin forwards TorchServe download
model requests to the Dragonfly P2P network.

The models download steps:

TorchServe sends a model download request and the request is forwarded to the Dragonfly Peer.

The Dragonfly Peer registers tasks with the Dragonfly Scheduler.

Return the candidate parents to Dragonfly Peer.

Dragonfly Peer downloads model from candidate parents.

After downloading the model, TorchServe will register the model.

## Installation

By integrating Dragonfly Endpoint into TorchServe, download traffic through Dragonfly to pull models stored in
S3, OSS, GCS, and ABS, and register models in TorchServe.
The Dragonfly Endpoint plugin is in the
dragonfly-endpoint
repository.

### Prerequisites

### Dragonfly Kubernetes Cluster Setup

For detailed installation documentation, please refer to
Lightweight Deployment
.

#### Prepare Kubernetes Cluster

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
to
match the download path of the object storage, configuration content is as follows:

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
-
regex
:
.
*amazonaws.*
```

Create a Dragonfly cluster using the configuration file:

```
$ helm repo add dragonfly https://dragonflyoss.github.io/helm-charts/
$ helm install --wait --create-namespace --namespace dragonfly-system dragonfly dragonfly/dragonfly -f charts-config.yaml
LAST DEPLOYED: Mon June 5 16:53:14 2024
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
$ kubectl get po -n dragonfly-system
NAME                                 READY   STATUS    RESTARTS      AGE
dragonfly-client-6jgzn               1/1     Running   0             17m
dragonfly-client-qzcz9               1/1     Running   0             17m
dragonfly-scheduler-0                1/1     Running   0             17m
dragonfly-scheduler-1                1/1     Running   0             17m
dragonfly-scheduler-2                1/1     Running   0             17m
dragonfly-seed-client-0              1/1     Running   0             17m
dragonfly-seed-client-1              1/1     Running   0             17m
dragonfly-seed-client-2              1/1     Running   0             17m
```

#### Expose the Proxy service port

Create the
dfstore.yaml
configuration to expose the port on which the Dragonfly Peer's HTTP proxy listens.
The default port is
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

### Install Dragonfly Endpoint plugin

#### Set environment variables for Dragonfly Endpoint configuration

Create
config.json
configuration，and set
DRAGONFLY_ENDPOINT_CONFIG
environment variable for
config.json
file path.

```
export DRAGONFLY_ENDPOINT_CONFIG=/etc/dragonfly-endpoint/config.json
```

The default configuration path is:

linux:
/etc/dragonfly-endpoint/config.json

darwin:
~/.dragonfly-endpoint/config.json

#### Dragonfly Endpoint configuration

Create the
config.json
configuration to configure the Dragonfly Endpoint for S3, the configuration is as follows:

Notice: Replace the
addr
address with your actual address.

```
{
"addr"
:
"http://127.0.0.1:4001"
,
"header"
:
{
}
,
"filter"
:
[
"X-Amz-Algorithm"
,
"X-Amz-Credential"
,
"X-Amz-Date"
,
"X-Amz-Expires"
,
"X-Amz-SignedHeaders"
,
"X-Amz-Signature"
]
,
"object_storage"
:
{
"type"
:
"s3"
,
"bucket_name"
:
"your_s3_bucket_name"
,
"region"
:
"your_s3_access_key"
,
"access_key"
:
"your_s3_access_key"
,
"secret_key"
:
"your_s3_access_key"
}
}
```

addr: The address of Dragonfly's Peer HTTP proxy.

header: Adds a request header to the request.

filter: Used to generate unique tasks and filter unnecessary query parameters in the URL.

object_storage: The object storage configuration, where type can be s3, oss, abs and gcs.

In the filter of the configuration, set different values when using different object storage:

In addition to S3, Dragonfly Endpoint plugin also supports OSS, GCS and ABS.
Different object storage configurations are as follows:

Notice: Replace the
addr
address with your actual address.

OSS(Object Storage Service)

```
{
"addr"
:
"http://127.0.0.1:4001"
,
"header"
:
{
}
,
"filter"
:
[
"Expires"
,
"Signature"
]
,
"object_storage"
:
{
"type"
:
"oss"
,
"bucket_name"
:
"your_oss_bucket_name"
,
"endpoint"
:
"your_oss_endpoint"
,
"access_key_id"
:
"your_oss_access_key_id"
,
"access_key_secret"
:
"your_oss_access_key_secret"
}
}
```

GCS(Google Cloud Storage)

```
{
"addr"
:
"http://127.0.0.1:4001"
,
"header"
:
{
}
,
"object_storage"
:
{
"type"
:
"gcs"
,
"bucket_name"
:
"your_gcs_bucket_name"
,
"project_id"
:
"your_gcs_project_id"
,
"service_account_path"
:
"your_gcs_service_account_path"
}
}
```

ABS(Azure Blob Storage)

```
{
"addr"
:
"http://127.0.0.1:4001"
,
"header"
:
{
}
,
"object_storage"
:
{
"type"
:
"abs"
,
"account_name"
:
"your_abs_account_name"
,
"account_key"
:
"your_abs_account_key"
,
"container_name"
:
"your_abs_container_name"
}
}
```

### TorchServe integrates Dragonfly Endpoint plugin

For detailed installation documentation, please refer to
TorchServe document
.

#### Binary installation

Install TorchServe dependencies and torch-model-archiver：

```
python ./ts_scripts/install_dependencies.py
conda install torchserve torch-model-archiver torch-workflow-archiver -c pytorch
```

Clone TorchServe repository：

```
git clone https://github.com/pytorch/serve.git
cd serve
```

Create
model-store
directory to store the models：

```
mkdir model-store
chmod 777 model-store
```

Create
plugins-path
directory to store the binaries of the plugin：

```
mkdir plugins-path
```

#### Package Dragonfly Endpoint plugin

Clone dragonfly-endpoint repository：

```
git clone https://github.com/dragonflyoss/dragonfly-endpoint.git
```

Build the dragonfly-endpoint project to generate file in the
build/libs
directory:

```
cd ./dragonfly-endpoint
gradle shadowJar
```

Note:
Due to the limitations of TorchServe's JVM, the best Java version for Gradle is 11,
as a higher version will cause the plugin to fail to parse.

Move the Jar file into the plugins-path directory:

```
mv build/libs/dragonfly_endpoint-1.0-all.jar  <your plugins-path>
```

Prepare the plugin configuration
config.json
, and use S3 as the object storage:

Notice: Replace the
addr
address with your actual address.

```
{
"addr": "http://127.0.0.1:4001",
"header": {
},
"filter": [
"X-Amz-Algorithm",
"X-Amz-Credential",
"X-Amz-Date",
"X-Amz-Expires",
"X-Amz-SignedHeaders",
"X-Amz-Signature"
],
"object_storage": {
"type": "s3",
"bucket_name": "your_s3_bucket_name",
"region": "your_s3_access_key",
"access_key": "your_s3_access_key",
"secret_key": "your_s3_access_key"
}
}
```

Set the environment variables for the configuration:

```
export DRAGONFLY_ENDPOINT_CONFIG=/etc/dragonfly-endpoint/config.json
```

--model-store
sets the previously created directory to store the models and
--plugins-path
sets
the previously created directory to store the plugins.Start the TorchServe with Dragonfly Endpoint plugin:

```
torchserve --start --model-store <path-to-model-store-file> --plugins-path=<path-to-plugin-jars>
```

#### Verify TorchServe binary

Prepare the model. Download a model from
Model ZOO
or
package the model refer to
Torch Model archiver for TorchServe
.
Use
squeezenet1_1_scripted.mar
model to verify：

```
wget https://torchserve.pytorch.org/mar_files/squeezenet1_1_scripted.mar
```

Upload the model to object storage. For detailed uploading the model to S3, please refer to
S3
。

```
# Download the command line tool
pip install awscli
# Configure the key as prompted
aws configure
# Upload file
aws s3 cp < local file path > s3://< bucket name >/< Target path >
```

TorchServe plugin is named Dragonfly, please refer to
TorchServe Register API
for details of plugin API. The
url
parameter are not supported and add the
file_name
parameter which is the model file name to download.
Download the model:

```
curl -X POST  "http://localhost:8081/dragonfly/models?file_name=squeezenet1_1.mar"
```

Verify the model download successful:

```
{
"Status": "Model "squeezenet1_1" Version: 1.0 registered with 0 initial workers. Use scale workers API to add workers for the model."
}
```

Added model worker for inference:

```
curl -v -X PUT "http://localhost:8081/models/squeezenet1_1?min_worker=1"
```

Check the number of worker is increased:


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[TorchServe](https://d7y.io/docs/next/operations/integrations/torchserve/)
