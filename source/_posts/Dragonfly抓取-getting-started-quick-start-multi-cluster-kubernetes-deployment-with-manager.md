---
title: Dragonfly 抓取：Deployment with Manager
date: 2026-09-14 09:07:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/getting-started/quick-start/multi-cluster-kubernetes/deployment-with-manager/>

---

Documentation for deploying Dragonfly on multi-cluster kubernetes using helm. A Dragonfly cluster manages cluster within
a network. If you have two clusters with disconnected networks, you can use two Dragonfly clusters to manage their own clusters.

The deployment in a multi-cluster kubernetes is to use a Dragonfly cluster to manage a kubernetes cluster,
and use a centralized manager service to manage multiple Dragonfly clusters. Because peer can only transmit data in
its own Dragonfly cluster, if a kubernetes cluster deploys a Dragonfly cluster, then a kubernetes cluster forms a p2p network,
and internal peers can only schedule and transmit data in a kubernetes cluster.

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

Create kind cluster configuration file
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
8080
labels
:
cluster
:
a
-
role
:
worker
labels
:
cluster
:
a
-
role
:
worker
labels
:
cluster
:
b
-
role
:
worker
labels
:
cluster
:
b
```

Create cluster using the configuration file:

```
kind create cluster --config kind-config.yaml
```

Switch the context of kubectl to kind cluster A:

```
kubectl config use-context kind-kind
```

## Kind loads Dragonfly image

Pull Dragonfly latest images:

```
docker pull dragonflyoss/scheduler:latest
docker pull dragonflyoss/manager:latest
docker pull dragonflyoss/client:latest
docker pull dragonflyoss/dfinit:latest
```

Kind cluster loads Dragonfly latest images:

```
kind load docker-image dragonflyoss/scheduler:latest
kind load docker-image dragonflyoss/manager:latest
kind load docker-image dragonflyoss/client:latest
kind load docker-image dragonflyoss/dfinit:latest
```

## Create Dragonfly cluster

The simple method means distinguishing clusters by directly specifying the schedulerClusterID.
The user directly specifies the cluster ID in dfdaemon to explicitly tell dfdaemon which scheduler cluster to connect to,
thus listing the corresponding schedulers from manager that should be used.

### Create Dragonfly cluster A

Create Dragonfly cluster A, the schedulers, seed peers, peers and centralized manager included in
the cluster should be installed using helm.

#### Create Dragonfly cluster A based on helm charts

Create Dragonfly cluster A charts configuration file
charts-config-cluster-a.yaml
, configuration content is as follows:

```
manager
:
# Enable manager. The manager is disabled by default.
enable
:
true
nodeSelector
:
cluster
:
a
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
nodeSelector
:
cluster
:
a
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
config
:
manager
:
# Specify the schedulerClusterID to distinguish different Dragonfly clusters.
schedulerClusterID
:
1
seedClient
:
nodeSelector
:
cluster
:
a
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
host
:
# Specify the schedulerClusterID to distinguish different Dragonfly clusters.
schedulerClusterID
:
1
client
:
nodeSelector
:
cluster
:
a
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
host
:
# Specify the schedulerClusterID to distinguish different Dragonfly clusters.
schedulerClusterID
:
1
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

Create Dragonfly cluster A using the configuration file:

```
$ helm repo add dragonfly https://dragonflyoss.github.io/helm-charts/
$ helm install --wait --create-namespace --namespace cluster-a dragonfly dragonfly/dragonfly -f charts-config-cluster-a.yaml
NAME: dragonfly
LAST DEPLOYED: Tue Apr 16 16:12:42 2024
NAMESPACE: cluster-a
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
1. Get the manager address by running these commands:
export MANAGER_POD_NAME=$(kubectl get pods --namespace cluster-a -l "app=dragonfly,release=dragonfly,component=manager" -o jsonpath={.items[0].metadata.name})
export MANAGER_CONTAINER_PORT=$(kubectl get pod --namespace cluster-a $MANAGER_POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
kubectl --namespace cluster-a port-forward $MANAGER_POD_NAME 8080:$MANAGER_CONTAINER_PORT
echo "Visit http://127.0.0.1:8080 to use your manager"
2. Get the scheduler address by running these commands:
export SCHEDULER_POD_NAME=$(kubectl get pods --namespace cluster-a -l "app=dragonfly,release=dragonfly,component=scheduler" -o jsonpath={.items[0].metadata.name})
export SCHEDULER_CONTAINER_PORT=$(kubectl get pod --namespace cluster-a $SCHEDULER_POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
kubectl --namespace cluster-a port-forward $SCHEDULER_POD_NAME 8002:$SCHEDULER_CONTAINER_PORT
echo "Visit http://127.0.0.1:8002 to use your scheduler"
3. Configure runtime to use dragonfly:
https://d7y.io/docs/getting-started/quick-start/kubernetes/
```

Check that Dragonfly cluster A is deployed successfully:

```
$ kubectl get po -n cluster-a
NAME                                READY   STATUS    RESTARTS   AGE
dragonfly-client-5gvz7              1/1     Running   0          51m
dragonfly-client-xvqmq              1/1     Running   0          51m
dragonfly-manager-dc6dcf87b-l88mr   1/1     Running   0          51m
dragonfly-mysql-0                   1/1     Running   0          51m
dragonfly-redis-master-0            1/1     Running   0          51m
dragonfly-redis-replicas-0          1/1     Running   0          51m
dragonfly-redis-replicas-1          1/1     Running   0          48m
dragonfly-redis-replicas-2          1/1     Running   0          39m
dragonfly-scheduler-0               1/1     Running   0          51m
dragonfly-seed-client-0             1/1     Running   0          51m
```

#### Create NodePort service of the manager REST service

Create the manager REST service configuration file
manager-rest-svc.yaml
,
configuration content is as follows:

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
manager
-
rest
namespace
:
cluster
-
a
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
nodePort
:
30950
port
:
8080
selector
:
app
:
dragonfly
component
:
manager
release
:
dragonfly
```

Create manager REST service using the configuration file:

```
kubectl apply -f manager-rest-svc.yaml -n cluster-a
```

#### Visit manager console

Visit address
localhost:8080
to see the manager console. Sign in the console with the default root user,
the username is
root
and password is
dragonfly
. To customize the initial password, refer to
Sign in
.

By default, Dragonfly will automatically create Dragonfly cluster A record in manager when
it is installed for the first time. You can click Dragonfly cluster A to view the details.

### Create Dragonfly cluster B

Create Dragonfly cluster B, you need to create a Dragonfly cluster record in the manager console first,
and the schedulers, seed peers and peers included in the Dragonfly cluster should be installed using helm.

#### Create Dragonfly cluster B in the manager console

Visit manager console and click the
ADD CLUSTER
button to add Dragonfly cluster B record.
Note that the IDC is set to
cluster-2
to match the peer whose IDC is
cluster-2
.

Create Dragonfly cluster B record successfully.

#### Use schedulerClusterID to distinguish different Dragonfly clusters

The peer needs the schedulerClusterID for listing schedulers from manager,
The schedulerClusterID of the peer are configured in peer YAML config,
the fields are
host.schedulerClusterID
. If this field configured,
other fields such as
host.location
,
host.idc
,
host.ip
and
host.hostname
will be ignored for listing schedulers.
Refer to
dfdaemon config
.

SchedulerClusterID
: The id of the scheduler cluster,
the peer will use this id to distinguish different Dragonfly scheduler clusters.
You can get the id after creating the cluster from the manager console.

#### Create Dragonfly cluster B based on helm charts

Create charts configuration with cluster information in the manager console.

scheduler.config.manager.schedulerClusterID
using the
Scheduler cluster ID
from
cluster-2
information in the manager console to specify the scheduler cluster.

client.config.host.schedulerClusterID
using the
Scheduler cluster ID
from
cluster-2
information in the manager console to specify the scheduler cluster.

externalManager.host
is host of the manager GRPC server.

externalRedis.addrs[0]
is address of the redis.

Create Dragonfly cluster B charts configuration file
charts-config-cluster-b.yaml
,
configuration content is as follows:

```
scheduler
:
nodeSelector
:
cluster
:
b
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
config
:
manager
:
# Specify the schedulerClusterID to distinguish different Dragonfly clusters.
schedulerClusterID
:
2
seedClient
:
nodeSelector
:
cluster
:
b
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
host
:
# Specify the schedulerClusterID to distinguish different Dragonfly clusters.
schedulerClusterID
:
2
client
:
nodeSelector
:
cluster
:
b
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
host
:
# Specify the schedulerClusterID to distinguish different Dragonfly clusters.
schedulerClusterID
:
2
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
manager
:
enable
:
false
externalManager
:
enable
:
true
host
:
dragonfly
-
manager.cluster
-
a.svc.cluster.local
restPort
:
8080
grpcPort
:
65003
redis
:
enable
:
false
externalRedis
:
addrs
:
-
dragonfly
-
redis
-
master.cluster
-
a.svc.cluster.local
:
6379
password
:
dragonfly
mysql
:
enable
:
false
```

Create Dragonfly cluster B using the configuration file:

```
$ helm install --wait --create-namespace --namespace cluster-b dragonfly dragonfly/dragonfly -f charts-config-cluster-b.yaml
NAME: dragonfly
LAST DEPLOYED: Tue Apr 16 15:49:42 2024
NAMESPACE: cluster-b
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
1. Get the scheduler address by running these commands:
export SCHEDULER_POD_NAME=$(kubectl get pods --namespace cluster-b -l "app=dragonfly,release=dragonfly,component=scheduler" -o jsonpath={.items[0].metadata.name})
export SCHEDULER_CONTAINER_PORT=$(kubectl get pod --namespace cluster-b $SCHEDULER_POD_NAME -o jsonpath="{.spec.containers[0].ports[0].containerPort}")
kubectl --namespace cluster-b port-forward $SCHEDULER_POD_NAME 8002:$SCHEDULER_CONTAINER_PORT
echo "Visit http://127.0.0.1:8002 to use your scheduler"
2. Configure runtime to use dragonfly:
https://d7y.io/docs/getting-started/quick-start/kubernetes/
```

Check that Dragonfly cluster B is deployed successfully:

```
$ kubectl get po -n cluster-b
NAME                      READY   STATUS    RESTARTS   AGE
dragonfly-client-f4897    1/1     Running   0          10m
dragonfly-client-m9k9f    1/1     Running   0          10m
dragonfly-scheduler-0     1/1     Running   0          10m
dragonfly-seed-client-0   1/1     Running   0          10m
```

Create dragonfly cluster B successfully.

## Using Dragonfly to distribute images for multi-cluster kubernetes

### Containerd pull image back-to-source for the first time through Dragonfly in cluster A

Pull
alpine:3.19
image in
kind-worker
node:

```
time docker exec -i kind-worker /usr/local/bin/crictl pull alpine:3.19
```


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Deployment with Manager](https://d7y.io/docs/next/getting-started/quick-start/multi-cluster-kubernetes/deployment-with-manager/)
