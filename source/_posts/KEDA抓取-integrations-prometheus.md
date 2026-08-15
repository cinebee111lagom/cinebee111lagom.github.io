---
title: KEDA 抓取：Integrate with Prometheus
date: 2026-09-14 09:10:00
tags:
  - KEDA
  - 抓取
  - 文档
categories:
  - KEDA 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://keda.sh/docs/2.20/integrations/prometheus/>

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

Integrate with Prometheus
Latest

Overview of all Prometheus metrics that KEDA provides

Availability:
v2.0+

## Prometheus Exporter Metrics

### Operator

The KEDA Operator exposes Prometheus metrics which can be scraped on port
8080
at
/metrics
. The following metrics are being gathered:

keda_build_info
- Info metric, with static information about KEDA build like: version, git commit and Golang runtime info.

keda_scaler_active
- This metric marks whether the particular scaler is active (value == 1) or in-active (value == 0).

keda_scaled_object_paused
- This metric indicates whether a ScaledObject is paused (value == 1) or un-paused (value == 0).

keda_scaler_metrics_value
- The current value for each scaler’s metric that would be used by the HPA in computing the target average.

keda_scaler_metrics_latency_seconds
- The latency of retrieving current metric from each scaler.

keda_scaler_detail_errors_total
- The number of errors encountered for each scaler.

keda_scaler_empty_upstream_responses_total
- The number of times a scaler returned an empty response from its upstream source (e.g. a Prometheus query returning no results).

keda_scaled_object_errors_total
- The number of errors that have occurred for each ScaledObject.

keda_scaled_job_errors_total
- The number of errors that have occurred for each ScaledJob.

keda_resource_registered_total
- Total number of KEDA custom resources per namespace for each custom resource type (CRD) handled by the operator.

keda_trigger_registered_total
- Total number of triggers per trigger type handled by the operator.

keda_internal_scale_loop_latency_seconds
- Total deviation (in seconds) between the expected execution time and the actual execution time for the scaling loop. This latency could be produced due to accumulated scalers latencies or high load. This is an internal metric.

keda_cloudeventsource_events_emitted_total
- Measured emitted cloudevents with destination of this emitted event (eventsink) and emitted state.

keda_cloudeventsource_events_queued
- The number of events that are in the emitting queue.

keda_scaler_http_requests_total
- Total number of outbound HTTP requests issued during scaler metric collection.

keda_scaler_http_request_duration_seconds
- Histogram of the duration in seconds of outbound HTTP requests issued during scaler metric collection.

keda_internal_metricsservice_grpc_server_started_total
- Total number of RPCs started on the server.

keda_internal_metricsservice_grpc_server_handled_total
- Total number of RPCs completed on the server, regardless of success or failure.

keda_internal_metricsservice_grpc_server_msg_received_total
- Total number of RPC stream messages received on the server.

keda_internal_metricsservice_grpc_server_msg_sent_total
- Total number of gRPC stream messages sent by the server.

keda_internal_metricsservice_grpc_server_handling_seconds
- Histogram of response latency (seconds) of gRPC that had been application-level handled by the server.

Metrics exposed by the
Operator SDK
framework as explained
here
.

Note: When you deploy the KEDA Operator without any scalers deployed, the only metric you will see is
keda_build_info
. As you deploy scalers, you will start to see some of the metrics listed above but it is dependant on the types of scalers you have deployed.

### Admission Webhooks

The KEDA Webhooks expose Prometheus metrics which can be scraped on port
8080
at
/metrics
. The following metrics are being gathered:

keda_webhook_scaled_object_validation_total
- The current value for scaled object validations.

keda_webhook_scaled_object_validation_errors
- The number of validation errors.

### Metrics Server

The KEDA Metrics Adapter exposes Prometheus metrics which can be scraped on port
8080
at
/metrics
. The following metrics are being gathered:

keda_internal_metricsservice_grpc_client_started_total
- Total number of RPCs started on the client.

keda_internal_metricsservice_grpc_client_handled_total
- Total number of RPCs completed by the client, regardless of success or failure.

keda_internal_metricsservice_grpc_client_msg_received_total
- Total number of RPC stream messages received by the client.

keda_internal_metricsservice_grpc_client_msg_sent_total
- Total number of gRPC stream messages sent by the client.

keda_internal_metricsservice_grpc_client_handling_seconds
- Histogram of response latency (seconds) of the gRPC until it is finished by the application.

Metrics exposed by the
Operator SDK
framework as explained
here
.

Metrics exposed (prepended with
apiserver_
) by
Kubernetes API Server

## Premade Grafana dashboard

A premade
Grafana dashboard
is available to visualize metrics exposed by the KEDA Metrics Adapter.

The dashboard has two sections:

Visualization of KEDA’s metric server

Visualization of the scale target and its changes in replicas scaled by KEDA

On top, the dashboard supports the following variables:

datasource

namespace

scaledObject

scaledJob

scaler

metric

---

> 完整与最新内容以官方文档为准：[Integrate with Prometheus](https://keda.sh/docs/2.20/integrations/prometheus/)
