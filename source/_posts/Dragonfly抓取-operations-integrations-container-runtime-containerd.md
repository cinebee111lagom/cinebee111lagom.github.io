---
title: Dragonfly 抓取：containerd
date: 2026-09-14 09:17:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/integrations/container-runtime/containerd/>

---

Documentation for setting Dragonfly's container runtime to containerd.

## Prerequisites

## Quick Start

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
docker pull dragonflyoss/dfinit:latest
```

Kind cluster loads Dragonfly latest images:

```
kind load docker-image dragonflyoss/scheduler:latest
kind load docker-image dragonflyoss/client:latest
kind load docker-image dragonflyoss/dfinit:latest
```

### Create Dragonfly cluster based on helm charts

Create the Helm Charts configuration file
values.yaml
. Please refer to the
configuration
documentation for details.

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
dfinit
:
enable
:
true
image
:
repository
:
dragonflyoss/dfinit
tag
:
latest
config
:
containerRuntime
:
containerd
:
configPath
:
/etc/containerd/config.toml
proxyAllRegistries
:
true
```

Create a Dragonfly cluster using the configuration file:

```
$ helm repo add dragonfly https://dragonflyoss.github.io/helm-charts/
$ helm install --wait --create-namespace --namespace dragonfly-system dragonfly dragonfly/dragonfly -f values.yaml
NAME: dragonfly
LAST DEPLOYED: Mon Apr 28 10:59:19 2024
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
NAME                                 READY   STATUS    RESTARTS      AGE
dragonfly-client-54vm5               1/1     Running   0             37m
dragonfly-client-cvbln               1/1     Running   0             37m
dragonfly-scheduler-0                1/1     Running   0             37m
dragonfly-seed-client-0              1/1     Running   2 (27m ago)   37m
```

### Containerd downloads images through Dragonfly

Pull
alpine:3.19
image in kind-worker node:

```
docker exec -i kind-worker /usr/local/bin/crictl pull alpine:3.19
```

#### Verify

You can execute the following command to check if the
alpine:3.19
image is distributed via Dragonfly.

```
# Find pod name.
export POD_NAME=$(kubectl get pods --namespace dragonfly-system -l "app=dragonfly,component=client" -o=jsonpath='{.items[?(@.spec.nodeName=="kind-worker")].metadata.name}' | head -n 1 )
# Find peer id.
export TASK_ID=$(kubectl -n dragonfly-system exec ${POD_NAME} -- sh -c "grep -hoP 'library/alpine.*task_id=\"\K[^\"]+' /var/log/dragonfly/dfdaemon/* | head -n 1")
# Check logs.
kubectl -n dragonfly-system exec -it ${POD_NAME} -- sh -c "grep ${TASK_ID} /var/log/dragonfly/dfdaemon/* | grep 'download task succeeded'"
```

The expected output is as follows:

```
{
2024-04-19T02:44:09.259458Z  INFO
"download_task":"dragonfly-client/src/grpc/dfdaemon_download.rs:276":: "download task succeeded"
"host_id": "172.18.0.3-kind-worker",
"task_id": "a46de92fcb9430049cf9e61e267e1c3c9db1f1aa4a8680a048949b06adb625a5",
"peer_id": "172.18.0.3-kind-worker-86e48d67-1653-4571-bf01-7e0c9a0a119d"
}
```

## More configurations

### Multiple Registries

#### Proxy all registries to Dragonfly

Method 1
: Deploy using Helm Charts and create the Helm Charts configuration file
values.yaml
.
Please refer to the
configuration
documentation for details.

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
dfinit
:
enable
:
true
image
:
repository
:
dragonflyoss/dfinit
tag
:
latest
config
:
containerRuntime
:
containerd
:
configPath
:
/etc/containerd/config.toml
proxyAllRegistries
:
true
```

Method 2
: Modify your
config.toml
(default location:
/etc/containerd/config.toml
), refer to
default-registry-configuration-examples
.

Notice: config_path is the path where containerd looks for registry configuration files.

```
# explicitly use v2 config format
version = 2
[plugins."io.containerd.grpc.v1.cri".registry]
config_path = "/etc/containerd/certs.d"
```

Create the default registry configuration file
/etc/containerd/certs.d/_default/hosts.toml
:

```
[host."http://127.0.0.1:4001"]
capabilities = ["pull", "resolve"]
```

Restart containerd:

```
systemctl restart containerd
```

#### Proxy specific registries to Dragonfly

Method 1
: Deploy using Helm Charts and create the Helm Charts configuration file
values.yaml
.
Please refer to the
configuration
documentation for details.

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
dfinit
:
enable
:
true
image
:
repository
:
dragonflyoss/dfinit
tag
:
latest
config
:
containerRuntime
:
containerd
:
configPath
:
/etc/containerd/config.toml
registries
:
-
hostNamespace
:
docker.io
serverAddr
:
https
:
//index.docker.io
capabilities
:
[
'pull'
,
'resolve'
]
-
hostNamespace
:
ghcr.io
serverAddr
:
https
:
//ghcr.io
capabilities
:
[
'pull'
,
'resolve'
]
```

Method 2
: Modify your
config.toml
(default location:
/etc/containerd/config.toml
), refer to
registry-configuration-examples
.

Notice: config_path is the path where containerd looks for registry configuration files.

```
# explicitly use v2 config format
version = 2
[plugins."io.containerd.grpc.v1.cri".registry]
config_path = "/etc/containerd/certs.d"
```

Create the registry configuration file
/etc/containerd/certs.d/docker.io/hosts.toml
:

Notice: The container registry is
https://index.docker.io
.

```
server = "https://index.docker.io"
[host."http://127.0.0.1:4001"]
capabilities = ["pull", "resolve"]
[host."http://127.0.0.1:4001".header]
X-Dragonfly-Registry = "https://index.docker.io"
```

Create the registry configuration file
/etc/containerd/certs.d/ghcr.io/hosts.toml
:

Notice: The container registry is
https://ghcr.io
.

```
server = "https://ghcr.io"
[host."http://127.0.0.1:4001"]
capabilities = ["pull", "resolve"]
[host."http://127.0.0.1:4001".header]
X-Dragonfly-Registry = "https://ghcr.io"
```

Restart containerd:

```
systemctl restart containerd
```

### Private project

Deploy using Helm Charts and create the Helm Charts configuration file
values.yaml
.
Please refer to the
configuration
documentation for details.

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
dfinit
:
enable
:
true
image
:
repository
:
dragonflyoss/dfinit
tag
:
latest
config
:
containerRuntime
:
containerd
:
configPath
:
/etc/containerd/config.toml
registries
:
-
hostNamespace
:
your_private_registry_host_addr
serverAddr
:
your_private_registry_server_addr
capabilities
:
[
'pull'
,
'resolve'
]
```

Modify your
config.toml
(default location:
/etc/containerd/config.toml
), refer to
configure-registry-credentials
.

Notice：
your_private_registry_host_addr
is your private registry host address.

```
[plugins."io.containerd.grpc.v1.cri".registry.configs."your_private_registry_host_addr".auth]
username = "your_private_registry_username"
password = "your_private_registry_password"
auth = "your_private_registry_token"
[plugins."io.containerd.grpc.v1.cri".registry.configs."127.0.0.1:4001".auth]
username = "your_private_registry_username"
password = "your_private_registry_password"
auth = "your_private_registry_token"
```

Restart containerd:

```
systemctl restart containerd
```

### Container Registry using self-signed certificates

Use Harbor as an example of a container registry using self-signed certificates.
Harbor generates self-signed certificate, refer to
Harbor
.

#### Install Dragonfly with Helm Charts

Create seed client secret configuration file
seed-client-secret.yaml
, configuration content is as follows:

Notice: yourdomain.crt is Harbor's ca.crt.

```
apiVersion
:
v1
kind
:
Secret
metadata
:
name
:
seed
-
client
-
secret
namespace
:
dragonfly
-
system
type
:
Opaque
data
:
# the data is abbreviated in this example.
yourdomain.crt
:
|
MIIFwTCCA6mgAwIBAgIUdgmYyNCw4t+Lp/...
```

Create the secret through the following command:

```
kubectl apply -f seed-client-secret.yaml
```

Create client secret configuration file
client-secret.yaml
, configuration content is as follows:

Notice: yourdomain.crt is Harbor's ca.crt.

```
apiVersion
:
v1
kind
:
Secret
metadata
:
name
:
client
-
secret
namespace
:
dragonfly
-
system
type
:
Opaque
data
:
# the data is abbreviated in this example.
yourdomain.crt
:
|
MIIFwTCCA6mgAwIBAgIUdgmYyNCw4t+Lp/...
```

Create the secret through the following command:

```
kubectl apply -f client-secret.yaml
```

Create helm charts configuration file
values.yaml
, configuration content is as follows:

Support preheating for harbor with self-signed certificates,
you need to change the
manager.config.job.preheat.tls
configuration,
/etc/certs/yourdomain.crt
is the harbor self-signed certificate configuration file.
If you want to bypass TLS verification, please set
insecureSkipVerify
to
true
.

Support dragonfly as registry of containerd for harbor with self-signed certificates,
you need to change the
client.config.proxy.registryMirror
configuration and
seedClient.config.proxy.registryMirror
configuration,
https://yourdomain.com
is the harbor service address,
/etc/certs/yourdomain.crt
is the harbor self-signed certificate configuration file.

Set the configuration of the containerd for harbor with self-signed certificates,
you need to change the
client.dfinit.config.containerRuntime.containerd.registries
configuration,
yourdomain.com
is harbor registry host address,
https://yourdomain.com
is the Harbor service address.
If you want to bypass TLS verification, please set
skipVerify
to
true
.


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[containerd](https://d7y.io/docs/next/operations/integrations/container-runtime/containerd/)
