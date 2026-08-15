---
title: Dragonfly 抓取：Lightweight Deployment
date: 2026-09-14 09:04:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/getting-started/quick-start/kubernetes/lightweight-deployment/>

---

Documentation for deploying Dragonfly on kubernetes using helm.

This is the recommended lightweight deployment, which runs Dragonfly without the Manager
and its MySQL and Redis dependencies. The scheduler and client load the dynamic configuration
from the local
dynconfig.yaml
file mounted as a ConfigMap instead of fetching it from the
Manager, and clients discover schedulers via the scheduler headless service.

## Runtime

You can have a quick start following
Helm Charts
.
It is recommended to use
containerd
.

## Setup kubernetes cluster

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

## Kind loads Dragonfly image

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

## Create Dragonfly cluster based on helm charts

Create helm charts configuration file
charts-config.yaml
, configuration content is as follows.
The Manager, MySQL and Redis are disabled by default, so the scheduler and client load the
dynamic configuration from the local
dynconfig.yaml
file mounted as a ConfigMap, refer to
scheduler config
and
dfdaemon config
.

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
$ helm install --wait --create-namespace --namespace dragonfly-system dragonfly dragonfly/dragonfly -f charts-config.yaml
NAME: dragonfly
LAST DEPLOYED: Mon Jul 27 21:23:00 2026
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
NAME                      READY   STATUS    RESTARTS   AGE
dragonfly-client-dhqfc    1/1     Running   0          3m
dragonfly-client-h58x6    1/1     Running   0          3m
dragonfly-scheduler-0     1/1     Running   0          3m
dragonfly-seed-client-0   1/1     Running   0          3m
```

## Containerd downloads images through Dragonfly

Pull
alpine:3.19
image in kind-worker node:

```
docker exec -i kind-worker /usr/local/bin/crictl pull alpine:3.19
```

### Verify

You can execute the following command to check if the
alpine:3.19
image is distributed via Dragonfly.

```
# Find pod name.
export POD_NAME=$(kubectl get pods --namespace dragonfly-system -l "app=dragonfly,release=dragonfly,component=client" -o=jsonpath='{.items[?(@.spec.nodeName=="kind-worker")].metadata.name}' | head -n 1 )
# Find task id.
export TASK_ID=$(kubectl -n dragonfly-system exec ${POD_NAME} -- sh -c "grep -hoP 'library/alpine.*task_id=\"\K[^\"]+' /var/log/dragonfly/dfdaemon/* | head -n 1")
# Check logs.
kubectl -n dragonfly-system exec -it ${POD_NAME} -- sh -c "grep ${TASK_ID} /var/log/dragonfly/dfdaemon/* | grep 'download task succeeded'"
# Download logs.
kubectl -n dragonfly-system exec ${POD_NAME} -- sh -c "grep ${TASK_ID} /var/log/dragonfly/dfdaemon/*" > dfdaemon.log
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

## Performance testing

### Containerd pull image back-to-source for the first time through Dragonfly

Pull
alpine:3.19
image in
kind-worker
node:

```
time docker exec -i kind-worker /usr/local/bin/crictl pull alpine:3.19
```

When pull image back-to-source for the first time through Dragonfly, it takes
37.852s
to download the
alpine:3.19
image.

### Containerd pull image hits the cache of remote peer

Delete the client whose Node is
kind-worker
to clear the cache of Dragonfly local Peer.

```
# Find pod name.
export POD_NAME=$(kubectl get pods --namespace dragonfly-system -l "app=dragonfly,release=dragonfly,component=client" -o=jsonpath='{.items[?(@.spec.nodeName=="kind-worker")].metadata.name}' | head -n 1 )
# Delete pod.
kubectl delete pod ${POD_NAME} -n dragonfly-system
```

Delete
alpine:3.19
image in
kind-worker
node:

```
docker exec -i kind-worker /usr/local/bin/crictl rmi alpine:3.19
```

Pull
alpine:3.19
image in
kind-worker
node:

```
time docker exec -i kind-worker /usr/local/bin/crictl pull alpine:3.19
```

When pull image hits cache of remote peer, it takes
6.942s
to download the
alpine:3.19
image.

### Containerd pull image hits the cache of local peer

Delete
alpine:3.19
image in
kind-worker
node:

```
docker exec -i kind-worker /usr/local/bin/crictl rmi alpine:3.19
```

Pull
alpine:3.19
image in
kind-worker
node:

```
time docker exec -i kind-worker /usr/local/bin/crictl pull alpine:3.19
```

When pull image hits cache of local peer, it takes
5.540s
to download the
alpine:3.19
image.

## Preheat image

Use
dfctl
to preheat images without the Manager, refer to
Preheat
.

---

> 完整与最新内容以官方文档为准：[Lightweight Deployment](https://d7y.io/docs/next/getting-started/quick-start/kubernetes/lightweight-deployment/)
