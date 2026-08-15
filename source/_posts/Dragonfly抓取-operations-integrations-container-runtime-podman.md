---
title: Dragonfly 抓取：Podman
date: 2026-09-14 09:21:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/integrations/container-runtime/podman/>

---

Documentation for setting Dragonfly's container runtime to Podman.

## Prerequisites

## Quick Start

### Setup kubernetes cluster

Minikube
is recommended if no Kubernetes cluster is available for testing.

Create a Minikube cluster.

```
minikube start --driver=podman --container-runtime=cri-o
```

Switch the context of kubectl to minikube cluster:

```
kubectl config use-context minikube
```

### Minikube loads Dragonfly image

Pull Dragonfly latest images:

```
docker pull dragonflyoss/scheduler:latest
docker pull dragonflyoss/client:latest
docker pull dragonflyoss/dfinit:latest
```

Minikube cluster loads Dragonfly latest images:

```
minikube image load dragonflyoss/scheduler:latest
minikube image load dragonflyoss/client:latest
minikube image load dragonflyoss/dfinit:latest
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
null
podman
:
configPath
:
/etc/containers/registries.conf
unqualifiedSearchRegistries
:
[
'registry.fedoraproject.org'
,
'registry.access.redhat.com'
,
'docker.io'
]
registries
:
-
prefix
:
docker.io
location
:
docker.io
```

Create a Dragonfly cluster using the configuration file:

```
$ helm repo add dragonfly https://dragonflyoss.github.io/helm-charts/
$ helm install --create-namespace --namespace dragonfly-system dragonfly dragonfly/dragonfly -f values.yaml
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

### Podman downloads images through Dragonfly

Pull
alpine:3.19
image in minikube node:

```
docker exec -i minikube /usr/bin/podman pull alpine:3.19
```

#### Verify

You can execute the following command to check if the
alpine:3.19
image is distributed via Dragonfly.

```
# Find pod name.
export POD_NAME=$(kubectl get pods --namespace dragonfly-system -l "app=dragonfly,release=dragonfly,component=client" -o=jsonpath='{.items[?(@.spec.nodeName=="minikube")].metadata.name}' | head -n 1 )
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
"host_id": "172.18.0.3-minikube",
"task_id": "a46de92fcb9430049cf9e61e267e1c3c9db1f1aa4a8680a048949b06adb625a5",
"peer_id": "172.18.0.3-minikube-86e48d67-1653-4571-bf01-7e0c9a0a119d"
}
```

## More configurations

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
client.dfinit.config.containerRuntime.podman.registries
configuration,
yourdomain.com
is the harbor registry host address. CRI-O skips TLS verification by default (no certificate required).

```
manager
:
# Enable manager. The manager is disabled by default.
enable
:
true
image
:
repository
:
dragonflyoss/manager
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
job
:
preheat
:
tls
:
insecureSkipVerify
:
false
caCert
:
/etc/certs/yourdomain.crt
extraVolumes
:
-
name
:
client
-
secret
secret
:
secretName
:
client
-
secret
extraVolumeMounts
:
-
name
:
client
-
secret
mountPath
:
/etc/certs
# MySQL and Redis are the dependencies of the manager,
# and they are disabled by default.
mysql
:
enable
:
true
redis
:
enable
:
true
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
config
:
proxy
:
registryMirror
:
addr
:
https
:
//yourdomain.com
cert
:
/etc/certs/yourdomain.crt
extraVolumes
:
-
name
:
seed
-
client
-
secret
secret
:
secretName
:
seed
-
client
-
secret
extraVolumeMounts
:
-
name
:
seed
-
client
-
secret
mountPath
:
/etc/certs
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
registryMirror
:
addr
:
https
:
//yourdomain.com
cert
:
/etc/certs/yourdomain.crt
extraVolumes
:
-
name
:
client
-
secret
secret
:
secretName
:
client
-
secret
extraVolumeMounts
:
-
name
:
client
-
secret
mountPath
:
/etc/certs
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
null
podman
:
configPath
:
/etc/containers/registries.conf
unqualifiedSearchRegistries
:
[
'registry.fedoraproject.org'
,
'registry.access.redhat.com'
,
'docker.io'
]
registries
:
-
prefix
:
yourdomain.com
location
:
yourdomain.com
```

#### Install Dragonfly with Binaries

Copy Harbor's ca.crt file to
/etc/containers/certs.d/yourdomain.crt
.

```
cp ca.crt /etc/containers/certs.d/yourdomain.crt
```

Install Dragonfly with Binaries, refer to
Binaries
.

To support preheating for harbor with self-signed certificates, the Manager configuration needs to be modified.

Configure
manager.yaml
, the default path is
/etc/dragonfly/manager.yaml
,
refer to
manager config
.

Notice:
yourdomain.crt
is Harbor's ca.crt.

```
job:
# Preheat configuration.
preheat:
tls:
# insecureSkipVerify controls whether a client verifies the server's certificate chain and hostname.
insecureSkipVerify: false
# # caCert is the CA certificate for preheat tls handshake, it can be path or PEM format string.
caCert: /etc/certs/yourdomain.crt
```

Skip TLS verification, set
job.preheat.tls.insecureSkipVerify
to true.

```
job:
# Preheat configuration.
preheat:
tls:
# insecureSkipVerify controls whether a client verifies the server's certificate chain and hostname.
insecureSkipVerify: true
# # caCert is the CA certificate for preheat tls handshake, it can be path or PEM format string.
# caCert: ''
```

Configure
dfdaemon.yaml
, the default path is
/etc/dragonfly/dfdaemon.yaml
,
refer to
dfdaemon config
.

```
host:
schedulerClusterID: 1
manager:
addr: http://dragonfly-manager:65003
seedPeer:
enable: true
type: super
proxy:
registryMirror:
# addr is the default address of the registry mirror. Proxy will start a registry mirror service for the
# client to pull the image. The client can use the default address of the registry mirror in
# configuration to pull the image. The `X-Dragonfly-Registry` header can instead of the default address
# of registry mirror.
addr: https://yourdomain.com
## cert is the client cert path with PEM format for the registry.
## If registry use self-signed cert, the client should set the
## cert for the registry mirror.
cert: /etc/certs/yourdomain.crt
```

Configure
dfdaemon.yaml
, the default path is
/etc/dragonfly/dfdaemon.yaml
,
refer to
dfdaemon config
.

```
manager:
addr: http://dragonfly-manager:65003
proxy:
registryMirror:
# addr is the default address of the registry mirror. Proxy will start a registry mirror service for the
# client to pull the image. The client can use the default address of the registry mirror in
# configuration to pull the image. The `X-Dragonfly-Registry` header can instead of the default address
# of registry mirror.
addr: https://yourdomain.com
## cert is the client cert path with PEM format for the registry.
## If registry use self-signed cert, the client should set the
## cert for the registry mirror.
cert: /etc/certs/yourdomain.crt
```

A custom TLS configuration for a container registry can be configured by creating a directory under
/etc/containers/certs.d
.
The name of the directory must correspond to the host
:port
of the registry (e.g., yourdomain.com
:port
),
refer to
containers-certs.d
.

```
cp yourdomain.com.cert /etc/containers/certs.d/yourdomain.com/
cp yourdomain.com.key /etc/containers/certs.d/yourdomain.com/
cp ca.crt /etc/containers/certs.d/yourdomain.com/
```

The following example illustrates a configuration that uses custom certificates.

```
/etc/containers/certs.d/    <- Certificate directory
└── yourdomain.com:port     <- Hostname:port
├── yourdomain.com.cert  <- Harbor certificate
├── yourdomain.com.key   <- Harbor key
└── ca.crt               <- Certificate authority that signed the registry certificate
```


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Podman](https://d7y.io/docs/next/operations/integrations/container-runtime/podman/)
