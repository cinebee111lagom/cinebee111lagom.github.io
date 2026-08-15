---
title: KEDA 抓取：Setup Autoscaling with KEDA
date: 2026-09-14 09:02:00
tags:
  - KEDA
  - 抓取
  - 文档
categories:
  - KEDA 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://keda.sh/docs/2.20/setupscaler/>

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

Setup Autoscaling with KEDA
Latest

Procedure to Setup a Scaler in KEDA

## Prerequisites

Kubernetes Cluster
:
Ensure you have a running Kubernetes cluster set up and accessible.
If you don’t have a cluster yet, follow the
official Kubernetes documentation
to create a new cluster suitable for your environment (local machine, cloud provider, etc.).

Kubernetes Cluster
:

Ensure you have a running Kubernetes cluster set up and accessible.

If you don’t have a cluster yet, follow the
official Kubernetes documentation
to create a new cluster suitable for your environment (local machine, cloud provider, etc.).

KEDA Installation
:
KEDA needs to be installed on your Kubernetes cluster before you can use it.
Follow the
KEDA installation guide
carefully, including any prerequisites specific to your Kubernetes setup.
The installation guide provides instructions for different installation methods (e.g., YAML, Helm charts, etc.). Choose the method that suits your needs.

KEDA Installation
:

KEDA needs to be installed on your Kubernetes cluster before you can use it.

Follow the
KEDA installation guide
carefully, including any prerequisites specific to your Kubernetes setup.

The installation guide provides instructions for different installation methods (e.g., YAML, Helm charts, etc.). Choose the method that suits your needs.

kubectl
:
The
kubectl
command-line tool is required to interact with your Kubernetes cluster.
Follow the
official kubectl installation guide
to install
kubectl
on your operating system.
Once installed, configure
kubectl
to communicate with your Kubernetes cluster by following the cluster-specific instructions provided by your Kubernetes setup.

kubectl
:

The
kubectl
command-line tool is required to interact with your Kubernetes cluster.

Follow the
official kubectl installation guide
to install
kubectl
on your operating system.

Once installed, configure
kubectl
to communicate with your Kubernetes cluster by following the cluster-specific instructions provided by your Kubernetes setup.

## Step 1: Identify the Scaler You Need

KEDA supports various scalers that correspond to different event sources or triggers. Determining the right scaler is crucial for scaling your application based on the desired event source.

Visit the
KEDA Scalers documentation
and browse through the list of available scalers.

Identify the scaler that matches the event source you want to use for scaling your application. For example:
If you want to scale based on incoming HTTP traffic, you would need the
HTTP Add-on
.
Note:
The HTTP Add-on is still in beta stage and may not provide the full functionality or stability expected in a production environment.
If you want to scale based on messages in a RabbitMQ queue, you would need the
RabbitMQ scaler
.
If you want to scale based on a cron schedule, you would need the
Cron scaler
.

If you want to scale based on incoming HTTP traffic, you would need the
HTTP Add-on
.
Note:
The HTTP Add-on is still in beta stage and may not provide the full functionality or stability expected in a production environment.

If you want to scale based on incoming HTTP traffic, you would need the
HTTP Add-on
.

Note:
The HTTP Add-on is still in beta stage and may not provide the full functionality or stability expected in a production environment.

If you want to scale based on messages in a RabbitMQ queue, you would need the
RabbitMQ scaler
.

If you want to scale based on a cron schedule, you would need the
Cron scaler
.

Open the documentation page for your chosen scaler and familiarize yourself with its specific requirements and configuration options.

## Step 2: Install the Required Scaler (if needed)

Some scalers are part of the core KEDA installation, while others need to be installed separately as add-ons.

Refer to the documentation of your chosen scaler to check if it needs to be installed separately.

If the scaler needs to be installed separately, follow the installation instructions provided in the scaler’s documentation carefully.
The installation process typically involves running a command (e.g.,
helm install
for Helm charts) or applying YAML manifests using
kubectl
.

The installation process typically involves running a command (e.g.,
helm install
for Helm charts) or applying YAML manifests using
kubectl
.

Verify that the scaler has been installed successfully by checking the output of the installation process or by running any provided verification commands.

## Step 3: Create a ScaledObject Configuration File

KEDA uses a custom resource called
ScaledObject
to define how your application should be scaled based on the chosen event source or trigger.

Create a new file (e.g.,
scaledobject.yaml
) in a text editor or using the command line.

Define the
ScaledObject
configuration in this file, following the structure and examples provided in the documentation of your chosen scaler.

Typically, the
ScaledObject
configuration includes the following sections:
metadata
: Specifies the name and namespace for the
ScaledObject
.
spec.scaleTargetRef
: Identifies the Kubernetes deployment or other resource that should be scaled.
spec.pollingInterval
(optional): Specifies how often KEDA should check for scaling events (defaults to 15 seconds).
spec.cooldownPeriod
(optional): Specifies the cool-down period in seconds after a scaling event (defaults to 300 seconds).
spec.maxReplicaCount
(optional): Specifies the maximum number of replicas to scale up to (defaults to 100).
spec.triggers
: Defines the specific configuration for your chosen scaler, including any required parameters or settings.

metadata
: Specifies the name and namespace for the
ScaledObject
.

spec.scaleTargetRef
: Identifies the Kubernetes deployment or other resource that should be scaled.

spec.pollingInterval
(optional): Specifies how often KEDA should check for scaling events (defaults to 15 seconds).

spec.cooldownPeriod
(optional): Specifies the cool-down period in seconds after a scaling event (defaults to 300 seconds).

spec.maxReplicaCount
(optional): Specifies the maximum number of replicas to scale up to (defaults to 100).

spec.triggers
: Defines the specific configuration for your chosen scaler, including any required parameters or settings.

Refer to the scaler’s documentation for detailed explanations and examples of the
triggers
section and any other required or optional configuration settings.

Save the
scaledobject.yaml
file after making the necessary modifications.

## Step 4: Apply the ScaledObject Configuration

Once you have created the
ScaledObject
configuration file, apply it to your Kubernetes cluster using
kubectl
:

Open a terminal or command prompt and navigate to the directory containing the
scaledobject.yaml
file.

Run the following command to apply the
ScaledObject
configuration:
kubectl apply -f scaledobject.yaml
scaledobject.keda.sh/<scaled-object-name> created

Run the following command to apply the
ScaledObject
configuration:

```
kubectl apply -f scaledobject.yaml
```

```
scaledobject.keda.sh/<scaled-object-name> created
```

Verify that the
ScaledObject
has been created successfully by running:
kubectl get scaledobjects
This should display the
ScaledObject
you just created.
NAME              SCALETARGETKIND   SCALETARGETNAME   MIN   MAX   TRIGGERS   AUTHENTICATION   READY   ACTIVE   FALLBACK   AGE
<scaled-object-name>   Deployment        <deployment-name>   1     10    cpu                    <none>            True    False    <none>      10s

Verify that the
ScaledObject
has been created successfully by running:

```
kubectl get scaledobjects
```

This should display the
ScaledObject
you just created.

```
NAME              SCALETARGETKIND   SCALETARGETNAME   MIN   MAX   TRIGGERS   AUTHENTICATION   READY   ACTIVE   FALLBACK   AGE
<scaled-object-name>   Deployment        <deployment-name>   1     10    cpu                    <none>            True    False    <none>      10s
```

After applying the
ScaledObject
configuration, KEDA will start monitoring the specified event source and scale your application accordingly, based on the configurations you provided.

## Step 5: Monitor Scaling Events

You can monitor the scaling events and logs generated by KEDA using the following commands:

List all
ScaledObjects
in your cluster:
kubectl get scaledobjects
This will show you the current state of your
ScaledObject
and the number of replicas.
NAME              SCALETARGETKIND   SCALETARGETNAME   MIN   MAX   TRIGGERS   AUTHENTICATION   READY   ACTIVE   FALLBACK   AGE
<scaled-object-name>   Deployment        <deployment-name>   1     10    cpu                    <none>            True    False    <none>      10s

List all
ScaledObjects
in your cluster:

```
kubectl get scaledobjects
```

This will show you the current state of your
ScaledObject
and the number of replicas.

```
NAME              SCALETARGETKIND   SCALETARGETNAME   MIN   MAX   TRIGGERS   AUTHENTICATION   READY   ACTIVE   FALLBACK   AGE
<scaled-object-name>   Deployment        <deployment-name>   1     10    cpu                    <none>            True    False    <none>      10s
```

View the logs of the KEDA operator:
kubectl logs -n keda -l
app
=
keda-operator
The KEDA operator logs will show you detailed information about scaling events, decisions made by KEDA based on the event source, and any errors or warnings.
{"level":"info","ts":<timestamp>,"logger":"scalehandler","msg":"Successfully scaled deployment","scaledobject.Namespace":"<namespace>","scaledobject.Name":"<scaled-object-name>","scaler":<scaler-type>}

View the logs of the KEDA operator:

```
kubectl logs -n keda -l
app
=
keda-operator
```

The KEDA operator logs will show you detailed information about scaling events, decisions made by KEDA based on the event source, and any errors or warnings.


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Setup Autoscaling with KEDA](https://keda.sh/docs/2.20/setupscaler/)
