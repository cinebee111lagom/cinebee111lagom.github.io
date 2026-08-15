---
title: KEDA 抓取：Integrate with OpenTelemetry Collector (Experimental)
date: 2026-09-14 09:11:00
tags:
  - KEDA
  - 抓取
  - 文档
categories:
  - KEDA 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://keda.sh/docs/2.20/integrations/opentelemetry/>

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

Integrate with OpenTelemetry Collector (Experimental)
Latest

Detail of integrating OpenTelemetry Collector in KEDA

Availability:
v2.12+

## Push Metrics to OpenTelemetry Collector (Experimental)

### Operator

The KEDA Operator supports outputting metrics to the OpenTelemetry collector. The parameter
--enable-opentelemetry-metrics=true
needs to be set. KEDA will push metrics to the OpenTelemetry collector specified by the
OTEL_EXPORTER_OTLP_ENDPOINT
environment variable.
OTEL_EXPORTER_OTLP_PROTOCOL
will also be used to choose HTTP or GRPC client. Other environment variables in OpenTelemetry are also supported (
https://opentelemetry.io/docs/concepts/sdk-configuration/otlp-exporter-configuration/)
. Here is an example configuration of the operator:

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: keda-operator
  ...
      containers:
        - name: keda-operator
          image: ghcr.io/kedacore/keda:latest
          command:
            - /keda
          args:
            --enable-opentelemetry-metrics=true
            ...
          ...
          env:
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: "http://opentelemetry-collector.default.svc.cluster.local:4318"
```

The following metrics are being gathered:

#### Deprecated metrics

The following metrics are exposed as well, but are deprecated and will be removed in KEDA v2.16.

|
keda.scaler.metrics.latency
| The latency of retrieving current metric from each scaler. |
|
keda.resource.totals
| Total number of KEDA custom resources per namespace for each custom resource type (CRD). |
|
keda.trigger.totals
| Total number of triggers per trigger type. |
|
keda.internal.scale.loop.latency
| Total deviation (in milliseconds) between the expected execution time and the actual execution time for the scaling loop. This latency could be produced due to accumulated scalers latencies or high load. This is an internal metric. |

---

> 完整与最新内容以官方文档为准：[Integrate with OpenTelemetry Collector (Experimental)](https://keda.sh/docs/2.20/integrations/opentelemetry/)
