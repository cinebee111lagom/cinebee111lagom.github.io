---
title: KEDA 抓取：Deploying KEDA
date: 2026-09-14 09:01:00
tags:
  - KEDA
  - 抓取
  - 文档
categories:
  - KEDA 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://keda.sh/docs/2.20/deploy/>

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

Deploying KEDA
Latest

KEDA offers multiple installation methods, each with unique benefits to suit various environments and needs. If you’re looking for flexibility and customization, deploying with
Helm
is ideal; it integrates well with environments that have established Helm workflows and allows easy configuration adjustments. For a straightforward setup, installing through
Operator Hub
provides a quick, one-click deployment with automatic updates, which is great for users seeking minimal customization.

Using
YAML files
offers the most control over your setup, making it perfect for environments requiring strict configurations or where Helm and Operator Hub are not options. Finally, deploying KEDA on
MicroK8s
is excellent for local or development testing, providing a lightweight Kubernetes environment that’s fast to set up without the commitment of a full cluster.

Each method balances convenience, control, and compatibility differently: Helm is best for extensive customization, Operator Hub for simplicity, YAML files for precise configuration, and MicroK8s for local experimentation. Select the option that aligns with your deployment requirements and environment.

💡
NOTE:
KEDA requires Kubernetes cluster version 1.30 and higher

Don’t see what you need? Feel free to
create an issue
on our GitHub repo.

## Deploying with Helm

### Prerequisites

To deploy KEDA using Helm, make sure Helm is installed and configured on your system. Helm is a package manager for Kubernetes that simplifies the deployment process by handling complex configurations and templating, which is particularly useful for managing multiple instances or custom settings. It’s recommended to use the latest version of Helm to ensure compatibility with KEDA and access to the newest features.

If you’re new to Helm, start by familiarizing yourself with basic Helm commands (
helm install
, helm upgrade, helm repo add
). Ensure that you have permissions to install charts on your Kubernetes cluster, as some environments may restrict access. A properly configured Helm setup will allow you to deploy KEDA quickly and make adjustments to configurations with ease.

### Installing

To deploy KEDA using Helm, first add the official KEDA Helm repository:
helm repo add kedacore https://kedacore.github.io/charts
helm repo update

To deploy KEDA using Helm, first add the official KEDA Helm repository:

```
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
```

Install
keda
by running:
Helm 3
helm install keda kedacore/keda --namespace keda --create-namespace
This command installs KEDA in a dedicated namespace (keda). You can customize the installation by passing additional configuration values with
--set
, allowing you to adjust parameters like replica counts, scaling metrics, or logging levels. Once installed, verify the deployment by checking the KEDA namespace for running pods:
kubectl get pods -n keda

Install
keda
by running:

Helm 3

```
helm install keda kedacore/keda --namespace keda --create-namespace
```

This command installs KEDA in a dedicated namespace (keda). You can customize the installation by passing additional configuration values with
--set
, allowing you to adjust parameters like replica counts, scaling metrics, or logging levels. Once installed, verify the deployment by checking the KEDA namespace for running pods:

```
kubectl get pods -n keda
```

To deploy KEDA’s Custom Resource Definitions (CRDs) separately from the Helm chart, follow these steps:

Download the CRD YAML File
: Visit the
KEDA GitHub releases page
and locate the
keda-2.xx.x-crds.yaml
file corresponding to your desired version.

Apply the CRDs to Your Cluster
: Use
kubectl
to apply the CRD definitions:
kubectl apply -f keda-2.xx.x-crds.yaml
Replace
2.xx.x
with the specific version number you downloaded.

Apply the CRDs to Your Cluster
: Use
kubectl
to apply the CRD definitions:

```
kubectl apply -f keda-2.xx.x-crds.yaml
```

Replace
2.xx.x
with the specific version number you downloaded.

By deploying the CRDs separately, you can manage them independently of the Helm chart, providing flexibility in your deployment process.

💡
NOTE:
When upgrading to KEDA version 2.2.1 or later, it’s important to address potential issues with CRDs. Starting with v2.2.1, KEDA’s Helm chart manages CRDs automatically, which can lead to upgrade failures if you previously installed KEDA using an earlier version. To prevent errors during the upgrade process, such as conflicts or failed deployments, consult KEDA’s
troubleshooting guide
for detailed instructions on resolving CRD-related issues.

Deploying KEDA with Helm is straightforward and allows easy updates and configuration adjustments, making it a flexible choice for most environments.

### Uninstalling

To uninstall KEDA, use the following Helm command:

```
helm uninstall keda –namespace keda
```

This command removes KEDA from your cluster while retaining your configuration files in case you need to reinstall later. If you also want to delete the keda namespace, run:

```
kubectl delete namespace keda
```

Uninstalling with Helm is efficient and keeps your cluster clean, especially if you’re testing configurations or upgrading to a new KEDA version.

You can remove finalizers with the following command:

```
kubectl patch scaledobject <resource-name> -p
'{"metadata":{"finalizers":null}}'
--type
=
merge
kubectl patch scaledjob <resource-name> -p
'{"metadata":{"finalizers":null}}'
--type
=
merge
```

Replace <
resource-name
> with the specific name of each resource. Removing finalizers ensures that these resources are fully removed, preventing any unintended orphaned resources in your cluster.

## Deploying with Operator Hub

### Prerequisites

Before deploying KEDA through Operator Hub, ensure you have access to a Kubernetes marketplace that supports Operator Hub (for example,
OpenShift
or an
Operator Lifecycle Manager
(OLM)-enabled cluster). You’ll also need the appropriate permissions to install operators in your cluster, as some environments may restrict access.

If you’re using OpenShift, you can access Operator Hub directly through the OpenShift Console. For other Kubernetes distributions, verify that the OLM is installed, as it manages the installation and lifecycle of operators from Operator Hub. Ensuring these prerequisites are met will allow for a smooth installation of KEDA from Operator Hub.

### Installing

To deploy KEDA through Operator Hub, start by navigating to your cluster’s Operator Hub interface. If you’re using OpenShift, access Operator Hub directly from the OpenShift Console. For other Kubernetes environments, ensure the
Operator Lifecycle Manager (OLM)
is installed.

Search for “KEDA” in Operator Hub, select the KEDA Operator, and click
Install
. Choose your preferred installation options, such as the target namespace, and confirm the installation. Once KEDA is installed, verify the deployment by checking that the KEDA Operator pod is running in the designated namespace.

On Operator Hub Marketplace locate and install KEDA operator to namespace
keda

Create
KedaController
resource named
keda
in namespace
keda
Using Operator Hub simplifies KEDA deployment, offering easy setup and automated lifecycle management within your Kubernetes environment.

💡
NOTE:
For more details on deploying KEDA with the Operator Hub installation method, refer to the official repository:

KEDA Operator Hub Repository

This repository provides additional guidance, configuration options, and troubleshooting tips for installing KEDA via Operator Hub in various Kubernetes environments.

For beginners exploring the
keda-olm-operator repository
, the following files and directories are particularly helpful:

-
README.md
:
This file provides an overview of the project, including installation instructions and usage examples. It’s a great starting point to understand the purpose and functionality of the operator.

-
config/samples/
: This directory contains sample YAML files that demonstrate how to configure KEDA resources. Reviewing these samples can help you learn how to define and apply custom resources in your Kubernetes cluster.

-
Makefile
: The
Makefile
includes commands for building and deploying the operator. Examining this file can give you insights into the development and deployment processes used in the project.

### Uninstalling

To uninstall KEDA, go to your cluster’s Operator Hub interface and locate the
Installed Operators
section. Find the KEDA Operator in the list, select it, and choose
Uninstall
. Confirm the uninstallation to remove the operator from your cluster.

If you deployed KEDA in a specific namespace, you may also want to delete that namespace to fully clean up any remaining resources. Uninstalling with Operator Hub keeps your cluster organized by removing all KEDA-related components with a few clicks.

## Deploying KEDA using the YAML files

### Prerequisites

Before deploying KEDA with YAML files, ensure you have
kubectl
installed and configured to interact with your Kubernetes cluster. You’ll also need the KEDA YAML manifests, which you can download from the
KEDA GitHub releases page
. This method provides full control over configuration and is ideal if you need a highly customized setup or don’t have access to Helm or Operator Hub. Make sure you have the appropriate permissions to apply these configurations in your cluster.

### Installing

Once the KEDA YAML manifests are downloaded, apply the files to your cluster with the following command:

```
# Including admission webhooks
kubectl apply --server-side -f https://github.com/kedacore/keda/releases/download/v2.20.0/keda-2.20.0.yaml
# Without admission webhooks
kubectl apply --server-side -f https://github.com/kedacore/keda/releases/download/v2.20.0/keda-2.20.0-core.yaml
```


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Deploying KEDA](https://keda.sh/docs/2.20/deploy/)
