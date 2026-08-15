---
title: Dragonfly 抓取：Helm Charts
date: 2026-09-14 09:03:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/getting-started/installation/helm-charts/>

---

Documentation for deploying Dragonfly on kubernetes using helm.

Dragonfly supports multiple deployment modes, refer to
Deployment Models
for the features of each deployment model:

Lightweight deployment (recommended)
: Deploy without the Manager and its MySQL and
Redis dependencies. The scheduler and client load the dynamic configuration from the local
dynconfig.yaml
file mounted as a ConfigMap instead of fetching it from the Manager, and
clients discover schedulers via the scheduler headless service. It is suitable for most
scenarios that only need the P2P distribution capabilities (e.g., small Kubernetes clusters,
edge environments, or CI systems).

Lightweight deployment with Redis
: Deploy Redis in addition to the lightweight
deployment. It additionally provides the persistent task and persistent cache task features,
whose metadata is stored in Redis.

Deployment with Manager
: Deploy the Manager along with MySQL and Redis. It additionally
provides the web console, Open API, preheating and multi-cluster management.

For more integrations such as Docker, CRI-O, Podman, Singularity/Apptainer, Nydus, eStargz, Harbor, Git LFS,
Hugging Face, TorchServe, Triton Server, Pip, etc. refer to
Integrations
.

## Prerequisites

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

Create the Helm Charts configuration file
values.yaml
, and set the container runtime to
containerd
.
Please refer to the
configuration
documentation for details.

The Manager, MySQL and Redis are disabled by default, so the scheduler and client load the
dynamic configuration from the local
dynconfig.yaml
file mounted as a ConfigMap, and clients
discover schedulers via the scheduler headless service. The local dynamic configuration can be
customized with the
scheduler.dynconfig
,
seedClient.dynconfig
and
client.dynconfig
values,
and updating it propagates the new configuration within one refresh interval, refer to
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
$ helm install --wait --create-namespace --namespace dragonfly-system dragonfly dragonfly/dragonfly -f values.yaml
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
dragonfly-client-gvspg    1/1     Running   0          3m
dragonfly-client-kxrhh    1/1     Running   0          3m
dragonfly-scheduler-0     1/1     Running   0          3m
dragonfly-seed-client-0   1/1     Running   0          3m
```

## Create Dragonfly cluster with Redis based on helm charts

If you need the persistent task and persistent cache task features, deploy Redis in addition
to the lightweight deployment, since their metadata is stored in Redis, refer to
Deployment Models
.

Create the Helm Charts configuration file
values.yaml
, configuration content is as follows:

```
# Deploy Redis to enable the persistent task and
# persistent cache task features.
redis
:
enable
:
true
# # Or use an existing Redis.
# externalRedis:
#   addrs:
#     - redis.example.com:6379
#   password: dragonfly
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
NAME                         READY   STATUS    RESTARTS   AGE
dragonfly-client-gvspg       1/1     Running   0          3m
dragonfly-client-kxrhh       1/1     Running   0          3m
dragonfly-redis-master-0     1/1     Running   0          3m
dragonfly-redis-replicas-0   1/1     Running   0          3m
dragonfly-redis-replicas-1   1/1     Running   0          2m
dragonfly-redis-replicas-2   1/1     Running   0          2m
dragonfly-scheduler-0        1/1     Running   0          3m
dragonfly-seed-client-0      1/1     Running   0          3m
```

## Create Dragonfly cluster with Manager based on helm charts

If you need the web console, Open API, preheating and multi-cluster management, deploy
Dragonfly with the Manager. The Manager, MySQL and Redis are disabled by default, so they
need to be enabled explicitly.

Pull and load the Manager latest image additionally:

```
docker pull dragonflyoss/manager:latest
kind load docker-image dragonflyoss/manager:latest
```

Create the Helm Charts configuration file
values.yaml
, configuration content is as follows:

```
manager
:
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
LAST DEPLOYED: Mon Jul 27 21:23:00 2026
NAMESPACE: dragonfly-system
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
1. Get the manager address by running these commands:
export MANAGER_POD_NAME=$(kubectl get pods --namespace dragonfly-system -l "app=dragonfly,release=dragonfly,component=manager" -o jsonpath={.items[0].metadata.name})
export MANAGER_CONTAINER_PORT=$(kubectl get pod --namespace dragonfly-system $MANAGER_POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
kubectl --namespace dragonfly-system port-forward $MANAGER_POD_NAME 8080:$MANAGER_CONTAINER_PORT
echo "Visit http://127.0.0.1:8080 to use your manager"
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
dragonfly-client-gvspg               1/1     Running   0             34m
dragonfly-client-kxrhh               1/1     Running   0             34m
dragonfly-manager-864774f54d-6t79l   1/1     Running   0             34m
dragonfly-mysql-0                    1/1     Running   0             34m
dragonfly-redis-master-0             1/1     Running   0             34m
dragonfly-redis-replicas-0           1/1     Running   0             34m
dragonfly-redis-replicas-1           1/1     Running   0             32m
dragonfly-redis-replicas-2           1/1     Running   0             32m
dragonfly-scheduler-0                1/1     Running   0             34m
dragonfly-seed-client-0              1/1     Running   5 (21m ago)   34m
```

## Containerd downloads images through Dragonfly

Pull
alpine:3.19
image in kind-worker node:

```
docker exec -i kind-worker /usr/local/bin/crictl pull alpine:3.19
```

You can execute the following command to check if the
alpine:3.19
image is distributed via Dragonfly.


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Helm Charts](https://d7y.io/docs/next/getting-started/installation/helm-charts/)
