---
title: KEDA 抓取：Migration Guide
date: 2026-09-14 09:08:00
tags:
  - KEDA
  - 抓取
  - 文档
categories:
  - KEDA 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://keda.sh/docs/2.20/migration/>

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

Migration Guide
Latest

## Migrating from KEDA v1 to v2

Please note that you
can not
run both KEDA v1 and v2 on the same Kubernetes cluster. You need to
uninstall
KEDA v1 first, in order to
install
and use KEDA v2.

💡
NOTE:
When uninstalling KEDA v1 make sure v1 CRDs are uninstalled from the cluster as well.

KEDA v2 is using a new API namespace for its Custom Resources Definitions (CRD):
keda.sh
instead of
keda.k8s.io
and introduces a new Custom Resource for scaling of Jobs. See full details on KEDA Custom Resources
here
.

Here’s an overview of what’s changed:

Scaling of Deployments

Scaling of Jobs

Improved flexibility & usability of trigger metadata

Scalers

TriggerAuthentication

### Scaling of Deployments

In order to scale
Deployments
with KEDA v2, you need to do only a few modifications to existing v1
ScaledObjects
definitions, so they comply with v2:

Change the value of
apiVersion
property from
keda.k8s.io/v1alpha1
to
keda.sh/v1alpha1

Rename property
spec.scaleTargetRef.deploymentName
to
spec.scaleTargetRef.name

Rename property
spec.scaleTargetRef.containerName
to
spec.scaleTargetRef.envSourceContainerName

Label
deploymentName
(in
metadata.labels.
) is no longer needed to be specified on v2 ScaledObject (it was mandatory on older versions of v1)

Please see the examples below or refer to the full
v2 ScaledObject Specification

Example of v1 ScaledObject

```
apiVersion
: keda.k8s.io/v1alpha1
kind
: ScaledObject
metadata
:
name
: { scaled-object-name }
labels
:
deploymentName
: { deployment-name }
spec
:
scaleTargetRef
:
deploymentName
: { deployment-name }
containerName
: { container-name }
pollingInterval
:
30
cooldownPeriod
:
300
minReplicaCount
:
0
maxReplicaCount
:
100
triggers
:
# {list of triggers to activate the deployment}
```

Example of v2 ScaledObject

```
apiVersion
: keda.sh/v1alpha1
#  <--- Property value was changed
kind
: ScaledObject
metadata
:
#  <--- labels.deploymentName is not needed
name
: { scaled-object-name }
spec
:
scaleTargetRef
:
name
: { deployment-name }
#  <--- Property name was changed
envSourceContainerName
: { container-name }
#  <--- Property name was changed
pollingInterval
:
30
cooldownPeriod
:
300
minReplicaCount
:
0
maxReplicaCount
:
100
triggers
:
# {list of triggers to activate the deployment}
```

### Scaling of Jobs

In order to scale
Jobs
with KEDA v2, you need to do only a few modifications to existing v1
ScaledObjects
definitions, so they comply with v2:

Change the value of
apiVersion
property from
keda.k8s.io/v1alpha1
to
keda.sh/v1alpha1

Change the value of
kind
property from
ScaledObject
to
ScaledJob

Remove property
spec.scaleType

Remove properties
spec.cooldownPeriod
and
spec.minReplicaCount

You can configure
successfulJobsHistoryLimit
and
failedJobsHistoryLimit
. They will remove the old job histories automatically.

Please see the examples below or refer to the full
v2 ScaledJob Specification

Example of v1 ScaledObject for Jobs scaling

```
apiVersion
: keda.k8s.io/v1alpha1
kind
: ScaledObject
metadata
:
name
: { scaled-object-name }
spec
:
scaleType
: job
jobTargetRef
:
parallelism
:
1
completions
:
1
activeDeadlineSeconds
:
600
backoffLimit
:
6
template
:
# {job template}
pollingInterval
:
30
cooldownPeriod
:
300
minReplicaCount
:
0
maxReplicaCount
:
100
triggers
:
# {list of triggers to create jobs}
```

Example of v2 ScaledJob

```
apiVersion
: keda.sh/v1alpha1
#  <--- Property value was changed
kind
: ScaledJob
#  <--- Property value was changed
metadata
:
name
: { scaled-job-name }
spec
:
#  <--- spec.scaleType is not needed
jobTargetRef
:
parallelism
:
1
completions
:
1
activeDeadlineSeconds
:
600
backoffLimit
:
6
template
:
# {job template}
pollingInterval
:
30
#  <--- spec.cooldownPeriod and spec.minReplicaCount are not needed
successfulJobsHistoryLimit
:
5
#  <--- property is added
failedJobsHistoryLimit
:
5
#  <--- Property is added
maxReplicaCount
:
100
triggers
:
# {list of triggers to create jobs}
```

### Improved flexibility & usability of trigger metadata

We’ve introduced more options to configure trigger metadata to give users more flexibility.

💡
NOTE:
Changes only apply to trigger metadata and don’t impact usage of
TriggerAuthentication

Here’s an overview:

### Scalers

Azure Service Bus

queueLength
was renamed to
messageCount

Kafka

authMode
property was replaced with
sasl
and
tls
properties. Please refer
documentation
for Kafka Authentication Parameters details.

RabbitMQ

In KEDA 2.0 the RabbitMQ scaler has only
host
parameter, and the protocol for communication can be specified by
protocol
(http or amqp). The default value is
amqp
. The behavior changes only for scalers that were using HTTP
protocol.

Example of RabbitMQ trigger before 2.0:

```
triggers
:
-
type
: rabbitmq
metadata
:
queueLength
:
"20"
queueName
: testqueue
includeUnacked
:
"true"
apiHost
:
"https://guest:password@localhost:443/vhostname"
```

The same trigger in 2.0:

```
triggers
:
-
type
: rabbitmq
metadata
:
queueLength
:
"20"
queueName
: testqueue
protocol
:
"http"
host
:
"https://guest:password@localhost:443/vhostname"
```

### TriggerAuthentication

In order to use Authentication via
TriggerAuthentication
with KEDA v2, you need to change:

Change the value of
apiVersion
property from
keda.k8s.io/v1alpha1
to
keda.sh/v1alpha1

For more details please refer to the full
v2 TriggerAuthentication Specification

---

> 完整与最新内容以官方文档为准：[Migration Guide](https://keda.sh/docs/2.20/migration/)
