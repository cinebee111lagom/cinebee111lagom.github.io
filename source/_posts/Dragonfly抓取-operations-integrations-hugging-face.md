---
title: Dragonfly 抓取：Hugging Face
date: 2026-09-14 09:26:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/integrations/hugging-face/>

---

This document will help you experience how to use dragonfly with hugging face.
During the downloading of datasets or models, the file size is large and
there are many services downloading the files at the same time.
The bandwidth of the storage will reach the limit and the download will be slow.

Dragonfly can be used to eliminate the bandwidth limit of the storage through P2P technology, thereby accelerating file downloading.

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
and set
client.config.proxy.registryMirror.addr
to
the address of the Hugging Face Hub's LFS server, configuration content is as follows:

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
registryMirror
:
addr
:
https
:
//cdn
-
lfs.huggingface.co
rules
:
-
regex
:
repos.*
useTLS
:
true
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
hf://
protocol

Note: To use dfget inside an inference container, you must install dfget and transfer file content from dfdaemon's Unix
domain socket. For details, refer to
Download in Container
.

Dragonfly's
dfget
command natively supports the
hf://
protocol, enabling direct P2P downloads from
Hugging Face Hub without any proxy configuration. This is the simplest way to download models and datasets
with Dragonfly acceleration.

### URL Format

The
hf://
URL format is:

```
hf://[<repo_type>/]<owner>/<repo>[/<path>]
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
dfget hf://meta-llama/Llama-2-7b/config.json -O /tmp/config.json
```

### Download a single file with authentication

For private repositories or to increase rate limits, use the
--hf-token
flag:

```
dfget hf://meta-llama/Llama-2-7b/config.json -O /tmp/config.json --hf-token=<token>
```

### Download an entire repository

Use the
--recursive
flag to download all files in a repository:

```
dfget hf://meta-llama/Llama-2-7b -O /tmp/llama-2-7b/ --recursive
```

### Download from a specific revision

Set
--hf-revision
to download from a specific branch, tag, or commit:

```
dfget hf://meta-llama/Llama-2-7b --hf-revision v1.0 -O /tmp/llama-2-7b/ --recursive
```

### Download a dataset

Prefix the URL with
datasets/
to download from a dataset repository:

```
# Download a specific file from a dataset.
dfget hf://datasets/rajpurkar/squad/train-v2.0.json -O /tmp/train.json
# Download an entire dataset.
dfget hf://datasets/rajpurkar/squad -O /tmp/squad/ --recursive
```

## Use Hub Python Library to download files and distribute traffic through Draognfly

Any API in the
Hub Python Library
that uses
Requests
library for downloading files can
distribute the download traffic in the P2P network by
setting
DragonflyAdapter
to the requests
Session
.

### Download a single file with Dragonfly

A single file can be downloaded using the
hf_hub_download
,
distribute traffic through the Dragonfly peer.

Create
hf_hub_download_dragonfly.py
file. Use
DragonflyAdapter
to forward the file download request of
the LFS protocol to Dragonfly HTTP proxy, so that it can use the P2P network
to distribute file, configuration content is as follows:

Notice: Replace the
session.proxies
address with your actual address.

```
import
requests
from
requests
.
adapters
import
HTTPAdapter
from
urllib
.
parse
import
urlparse
from
huggingface_hub
import
hf_hub_download
from
huggingface_hub
import
configure_http_backend
class
DragonflyAdapter
(
HTTPAdapter
)
:
def
get_connection
(
self
,
url
,
proxies
=
None
)
:
# Change the schema of the LFS request to download large files from https:// to http://,
# so that Dragonfly HTTP proxy can be used.
if
url
.
startswith
(
'https://cdn-lfs.huggingface.co'
)
:
url
=
url
.
replace
(
'https://'
,
'http://'
)
return
super
(
)
.
get_connection
(
url
,
proxies
)
def
add_headers
(
self
,
request
,
**
kwargs
)
:
super
(
)
.
add_headers
(
request
,
**
kwargs
)
# If there are multiple different LFS repositories, you can override the
# default repository address by adding X-Dragonfly-Registry header.
if
request
.
url
.
find
(
'example.com'
)
!=
-
1
:
request
.
headers
[
"X-Dragonfly-Registry"
]
=
'https://example.com'
# Create a factory function that returns a new Session.
def
backend_factory
(
)
-
>
requests
.
Session
:
session
=
requests
.
Session
(
)
session
.
mount
(
'http://'
,
DragonflyAdapter
(
)
)
session
.
mount
(
'https://'
,
DragonflyAdapter
(
)
)
session
.
proxies
=
{
'http'
:
'http://127.0.0.1:4001'
}
return
session
# Set it as the default session factory
configure_http_backend
(
backend_factory
=
backend_factory
)
hf_hub_download
(
repo_id
=
"tiiuae/falcon-rw-1b"
,
filename
=
"pytorch_model.bin"
)
```

Download a single file of th LFS protocol with Dragonfly:

```
$ python3 hf_hub_download_dragonfly.py
(…)YkNX13a46FCg__&Key-Pair-Id=KVTP0A1DKRTAX: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 2.62G/2.62G [00:52<00:00, 49.8MB/s]
```

#### Verify a single file download with Dragonfly

Execute the command:

```
# Find pod name.
export POD_NAME=$(kubectl get pods --namespace dragonfly-system -l "app=dragonfly,release=dragonfly,
component=client" -o=jsonpath='{.items[?(@.spec.nodeName=="kind-worker")].metadata.name}' | head -n 1 )
# Check logs.
kubectl -n dragonfly-system exec -it ${POD_NAME} -- grep "download task succeeded" /var/log/dragonfly/dfdaemon/*
```

The expected output is as follows:

```
2024-04-19T02:44:09.259458Z  INFO
"download_task":"dragonfly-client/src/grpc/dfdaemon_download.rs:276":: "download task succeeded"
"host_id": "172.18.0.3-kind-worker",
"task_id": "a46de92fcb9430049cf9e61e267e1c3c9db1f1aa4a8680a048949b06adb625a5",
"peer_id": "172.18.0.3-kind-worker-86e48d67-1653-4571-bf01-7e0c9a0a119d"
```

### Download a snapshot of the repo with Dragonfly

A snapshot of the repo can be downloaded using the
snapshot_download
,
distribute traffic through the Dragonfly peer.

Create
snapshot_download_dragonfly.py
file. Use
DragonflyAdapter
to forward the file download request of
the LFS protocol to Dragonfly HTTP proxy, so that it can use the P2P network
to distribute file. Only the files of the LFS protocol will be distributed
through the Dragonfly P2P network. content is as follows:

Notice: Replace the
session.proxies
address with your actual address.

```
import
requests
from
requests
.
adapters
import
HTTPAdapter
from
urllib
.
parse
import
urlparse
from
huggingface_hub
import
snapshot_download
from
huggingface_hub
import
configure_http_backend
class
DragonflyAdapter
(
HTTPAdapter
)
:
def
get_connection
(
self
,
url
,
proxies
=
None
)
:
# Change the schema of the LFS request to download large files from https:// to http://,
# so that Dragonfly HTTP proxy can be used.
if
url
.
startswith
(
'https://cdn-lfs.huggingface.co'
)
:
url
=
url
.
replace
(
'https://'
,
'http://'
)
return
super
(
)
.
get_connection
(
url
,
proxies
)
def
add_headers
(
self
,
request
,
**
kwargs
)
:
super
(
)
.
add_headers
(
request
,
**
kwargs
)
# If there are multiple different LFS repositories, you can override the
# default repository address by adding X-Dragonfly-Registry header.
if
request
.
url
.
find
(
'example.com'
)
!=
-
1
:
request
.
headers
[
"X-Dragonfly-Registry"
]
=
'https://example.com'
# Create a factory function that returns a new Session.
def
backend_factory
(
)
-
>
requests
.
Session
:
session
=
requests
.
Session
(
)
session
.
mount
(
'http://'
,
DragonflyAdapter
(
)
)
session
.
mount
(
'https://'
,
DragonflyAdapter
(
)
)
session
.
proxies
=
{
'http'
:
'http://127.0.0.1:4001'
}
return
session
# Set it as the default session factory
configure_http_backend
(
backend_factory
=
backend_factory
)
snapshot_download
(
repo_id
=
"tiiuae/falcon-rw-1b"
)
```

Download a snapshot of the repo with Dragonfly:


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Hugging Face](https://d7y.io/docs/next/operations/integrations/hugging-face/)
