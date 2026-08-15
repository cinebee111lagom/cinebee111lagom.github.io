---
title: KEDA 抓取：Troubleshooting KEDA API Server Throttling
date: 2026-09-14 09:09:00
tags:
  - KEDA
  - 抓取
  - 文档
categories:
  - KEDA 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://keda.sh/docs/2.20/troubleshooting/>

---

Setup Autoscaling with KEDA

Deploying KEDA

Migration Guide

Troubleshooting

Scaling Deployments, StatefulSets & Custom Resources

Scaling Jobs

Authentication

External Scalers

Admission Webhooks

Troubleshooting

Admission Webhooks

CloudEvent Support

Cluster

KEDA Metrics Server

Schema

Security

Glossary

FAQ

Events reference

ScaledObject specification

ScaledJob specification

ActiveMQ

ActiveMQ Artemis

Apache Kafka

Apache Kafka (Experimental)

Apache Pulsar

ArangoDB

AWS CloudWatch

AWS DynamoDB

AWS DynamoDB Streams

AWS Kinesis Stream

AWS SQS Queue

Azure Application Insights

Azure Blob Storage

Azure Data Explorer

Azure Event Hubs

Azure Log Analytics

Azure Monitor

Azure Pipelines

Azure Service Bus

Azure Storage Queue

Beanstalkd

Cassandra

CouchDB

CPU

Cron

Datadog

Dynatrace

Elastic Forecast (Experimental)

Elasticsearch

Etcd

External

External Push

Forgejo

Github Runner Scaler

Google Cloud Platform Cloud Tasks

Google Cloud Platform Pub/Sub

Google Cloud Platform Stackdriver

Google Cloud Platform Storage

Graphite

Huawei Cloudeye

IBM MQ

InfluxDB

Kubernetes Resource

Kubernetes Workload

Liiklus Topic

Loki

Memory

Metrics API

MongoDB

MSSQL

MySQL

NATS JetStream

NATS Streaming

New Relic

NSQ

OpenSearch

OpenStack Metric

OpenStack Swift

PostgreSQL

Predictkube

Prometheus

RabbitMQ Queue

Redis Lists

Redis Lists (supports Redis Cluster)

Redis Lists (supports Redis Sentinel)

Redis Streams

Redis Streams (supports Redis Cluster)

Redis Streams (supports Redis Sentinel)

Selenium Grid Scaler

Solace PubSub+ Event Broker

Solace PubSub+ Event Broker - Direct Messaging

SolarWinds

Solr

Splunk

Splunk Observability

Sumo Logic

Temporal

AWS (IRSA) Pod Identity Webhook

AWS EKS Pod Identity Webhook

AWS Secret Manager

Azure AD Workload Identity

Azure Key Vault secret

Bound service account token

Config Map

Environment variable

File path

GCP Secret Manager

GCP Workload Identity

Hashicorp Vault secret

OAuth2

Secret

Integrate with OpenTelemetry Collector (Experimental)

Integrate with Prometheus

KEDA Integration with Istio

Troubleshooting
Latest

How to address commonly encountered KEDA issues

If while setting up KEDA, you get an error:
(v1beta1.external.metrics.k8s.io) status FailedDiscoveryCheck
with a message:
failing or missing response from https://POD-IP:6443/apis/external.metrics.k8s.io/v1beta1: Get "https://POD-IP:6443/apis/external.metrics.k8s.io/v1beta1": Address is not allowed
.

One of the reason for this can be due to CNI like Cilium or any other.

### Before you start

Make sure no network policies are blocking traffic and required CIDR’s are added

### Check the status:

Find the api service name for the service
keda/keda-metrics-apiserver
:

```
kubectl get apiservice --all-namespaces
```

Check for the status of the api service found in previous step:

```
kubectl get apiservice <apiservicename> -o yaml
```

Example:

```
kubectl get apiservice v1beta1.external.metrics.k8s.io -o yaml
```

If the status is
False
, then there seems to be an issue and network might be the primary reason for it.

### Solution for managed Kubernetes services:

In managed Kubernetes services you might solve the issue by updating deployment file of metric-apiserver as below.

```
dnsPolicy
: ClusterFirst
hostNetwork
:
true
```

Eg:
Modify
useHostNetwork in values file.

If while setting up KEDA, you get an error:
(v1beta1.external.metrics.k8s.io) status FailedDiscoveryCheck
with a message:
no response from https://ip:443: Get https://ip:443: net/http: request canceled while waiting for connection (Client.Timeout exceeded while awaiting headers)
.

One of the reason for this can be that you are behind a proxy network.

### Before you start

Make sure no network policies are blocking traffic

### Check the status

Find the api service name for the service
keda/keda-metrics-apiserver
:

```
kubectl get apiservice --all-namespaces
```

Check for the status of the api service found in previous step:

```
kubectl get apiservice <apiservicename> -o yaml
```

Example:

```
kubectl get apiservice v1beta1.external.metrics.k8s.io -o yaml
```

If the status is
False
, then there seems to be an issue and proxy network might be the primary reason for it.

### Solution for self-managed Kubernetes cluster

Find the cluster IP for the
keda-metrics-apiserver
and
keda-operator-metrics
:

```
kubectl get services --all-namespaces
```

In the
/etc/kubernetes/manifests/kube-apiserver.yaml
- add the cluster IPs found in the previous step in no_proxy variable.

Reload systemd manager configuration:

```
sudo systemctl daemon-reload
```

Restart kubelet:

```
sudo systemctl restart kubelet
```

Check the API service status and the pods now. Should work!

### Solution for managed Kubernetes services

In managed Kubernetes services you might solve the issue by updating firewall rules in your cluster.

#### Google Kubernetes Engine (GKE)

E.g. in GKE private cluster
add
port 6443 (kube-apiserver) to allowed ports in master node firewall rules.

Also, if you are using Network Policies in your
kube-system
namespace, make sure they don’t block access for the konnectivity agent via port 6443. You can read more about
konnectivity service
.

In that case, you need to add a similar NetworkPolicy in the
kube-system
namespace:

```
---
apiVersion
: networking.k8s.io/v1
kind
: NetworkPolicy
metadata
:
name
: allow-egress-from-konnectivity-agent-to-keda
namespace
: kube-system
spec
:
egress
:
-
ports
:
-
port
:
6443
protocol
: TCP
to
:
-
ipBlock
:
cidr
: ${KUBE_POD_IP_CIDR}
podSelector
:
matchLabels
:
k8s-app
: konnectivity-agent
policyTypes
:
- Egress
```

#### Amazon Elastic Kubernetes Service (EKS)

E.g. Make sure the Cluster Security group can reach the Nodegroups on TCP 6443. For example, using the
terraform eks module
, this is achievable through the addtional nodegroup rules

```
module
"eks"
{
source
=
"terraform-aws-modules/eks/aws"
version
=
"19.5.1"
...
create_node_security_group
=
true
node_security_group_additional_rules
=
{
keda_metrics_server_access
=
{
description
=
"Cluster access to keda metrics"
protocol
=
"tcp"
from_port
=
6443
to_port
=
6443
type
=
"ingress"
source_cluster_security_group
=
true
}
}
```

As of version
19.6.0
of the
terraform-aws-modules/eks/aws
module it is enough to have
node_security_group_enable_recommended_rules
option enabled(default) to get neccessary security group ingress rule.

When KEDA has upstream errors to get scaler source information it will keep the current instance count of the workload unless the
fallback
section is defined.

This behavior might feel like the autoscaling is not happening, but in reality, it is because of problems related to the scaler source.

You can check if this is your case by reviewing the logs from the KEDA pods where you should see errors in both our Operator and Metrics server. You can also check a status of the ScaledObject (
READY
and
ACTIVE
condition) by running following command:

```
$ kubectl get scaledobject MY-SCALED-OBJECT
```

If you’re encountering the following error when trying to apply a
ScaledObject
using the
kubectl apply
command:

```
kubectl apply -f nginx-scaledobject.yaml
```

And receive an error like:

Error from server (Timeout): error when applying patch:
{"metadata":{"annotations":{"kubectl.kubernetes.io/last-applied-configuration":"{\"apiVersion\":\"keda.sh/v1alpha1\",\"kind\":\"ScaledObject\",\"metadata\":{\"annotations\":{},\"name\":\"nginx-scaledobject\",\"namespace\":\"default\"},\"spec\":{\"cooldownPeriod\":300,\"maxReplicaCount\":2,\"minReplicaCount\":1,\"pollingInterval\":3,\"scaleTargetRef\":{\"name\":\"nginx-deploy\"},\"triggers\":[{\"metadata\":{\"type\":\"Utilization\",\"value\":\"90\"},\"type\":\"cpu\"}]}}\n"}},"spec":{"maxReplicaCount":2}}
to:
Resource: "keda.sh/v1alpha1, Resource=scaledobjects", GroupVersionKind: "keda.sh/v1alpha1, Kind=ScaledObject"
Name: "nginx-scaledobject", Namespace: "default"
for: "nginx-scaledobject.yaml": error when patching "nginx-scaledobject.yaml": Timeout: request did not complete within requested timeout - context deadline exceeded
.

### Root cause

This issue commonly occurs when the KEDA admission webhook is not reachable by the Kubernetes control plane due to a network connectivity issue, typically on port 9443, which the webhook listens on.

### Solution (For Managed Kubernetes Services)

Step 1
: Enable Debug Logging on the Webhook
This helps confirm whether the request is reaching the webhook.

Option A
: If KEDA was installed via Helm:

Update your values.yaml file:

```
webhooks:
level: debug
```

Then upgrade your Helm release:

```
helm upgrade <release-name> kedacore/keda -n keda -f values.yaml
```

Option B
: If KEDA was installed manually (without Helm):

Edit the webhook deployment:

```
kubectl edit deployment keda-admission-webhooks -n keda
```

Add or update the arguments to include:

```
args:
-
"--zap-log-level=debug"
```

Step 2
: Check Webhook Logs
To confirm if the webhook is receiving the request:

```
kubectl logs -l
app
=
keda-admission-webhooks -n keda
```

If no logs appear when you run
kubectl apply
, it means the webhook pod is not being reached.

Step 3
: Check Network Connectivity
Ensure port 9443 is open between:

The Kubernetes control plane (where
kubectl apply
runs)

The nodes hosting the
keda-admission-webhooks
pod

This often involves configuring firewall rules or security groups to allow traffic from the control plane IP range to the node IP range on port 9443.

### Final Test:

After opening port
9443
, try applying your ScaledObject again:

```
kubectl apply -f nginx-scaledobject.yaml
```

If the webhook logs now show activity and the resource is created or properly rejected, the issue is resolved.

If you are experiencing messages like “Waited for … due to client-side throttling” in your KEDA operator logs, it might indicate that the KEDA operator is being throttled by the Kubernetes API server. This can happen in environments with a large number of
ScaledObject
resources.

KEDA provides several command-line flags to control its interaction with the Kubernetes API server. Adjusting these flags can help alleviate client-side throttling.

## Key Configuration Parameters

The following flags are relevant for tuning KEDA’s API server interaction:

--kube-api-qps
(Default:
20.0
): This flag sets the maximum queries per second (QPS) that the KEDA operator can make to the Kubernetes API server.

--kube-api-burst
(Default:
30
): This flag sets the maximum burst of requests that the KEDA operator can make to the Kubernetes API server.

The following env variable is relevant for tuning KEDA’s API server interaction:

KEDA_SCALEDOBJECT_CTRL_MAX_RECONCILES
(Default:
5
): This environment variable determines the maximum number of
ScaledObject
resources that the KEDA operator will reconcile concurrently.

## Recommendation for Adjusting Flags

In environments with a large number of
ScaledObject
resources (e.g., 400 or more), the default values for these parameters might be too low.

It is recommended to experiment with increasing the values of these parameters:

--kube-api-qps
and
--kube-api-burst
: Increasing these values allows the KEDA operator to make more requests to the API server per unit of time.
Consider starting by doubling the default values (e.g., set
--kube-api-qps=40
and
--kube-api-burst=60
).
Monitor the impact on both KEDA’s performance and the API server’s load.

Consider starting by doubling the default values (e.g., set
--kube-api-qps=40
and
--kube-api-burst=60
).

Monitor the impact on both KEDA’s performance and the API server’s load.

KEDA_SCALEDOBJECT_CTRL_MAX_RECONCILES
: Increasing this value allows KEDA to process more
ScaledObject
resources in parallel. However, this will also increase the overall load on the API server.
Consider a moderate increase (e.g., to
10
).
Observe the performance and API server load.


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Troubleshooting KEDA API Server Throttling](https://keda.sh/docs/2.20/troubleshooting/)
