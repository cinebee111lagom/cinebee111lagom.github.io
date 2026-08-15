---
title: KEDA 抓取：KEDA Integration with Istio
date: 2026-09-14 09:12:00
tags:
  - KEDA
  - 抓取
  - 文档
categories:
  - KEDA 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://keda.sh/docs/2.20/integrations/istio-integration/>

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

KEDA Integration with Istio
Latest

Guidance for running KEDA along with Istio in your cluster

Availability:
v2.14+

## Overview

Integrating KEDA with Istio can present challenges, particularly in environments with enforced mTLS. This document provides guidance on how to configure KEDA to work within an Istio service mesh without disabling Istio sidecar injection. This solution allows KEDA components to communicate securely and effectively while maintaining compliance with security requirements.

This can be considered as workaround, however it’s perfectly valid from the security standpoint.
Keda is still using own mTLS certificates for secure communication between it’s components and at the same time it’s able to communicate with Istio Mesh services (like Prometheus) through Istio sidecar proxies.

## Background

In some scenarios, users might face issues with KEDA components failing discovery checks when Istio sidecar injection is enabled. The current
troubleshooting guide
suggests disabling Istio sidecar injection in the KEDA namespace. However, if this is not feasible due to security policies, the following workaround can be applied.

### Requirements

Istio version >= 1.18.*

Kubernetes cluster with KEDA installed

### Example configuration

values.yaml
fragment for the
helm chart

```
... 

podAnnotations:
  # -- Pod annotations for KEDA operator
  keda:
    traffic.sidecar.istio.io/excludeInboundPorts: "9666"
    traffic.sidecar.istio.io/excludeOutboundPorts: "9443,6443"
  # -- Pod annotations for KEDA Metrics Adapter
  metricsAdapter:
    traffic.sidecar.istio.io/excludeInboundPorts: "6443"
    traffic.sidecar.istio.io/excludeOutboundPorts: "9666,9443"
  # -- Pod annotations for KEDA Admission webhooks
  webhooks:
    traffic.sidecar.istio.io/excludeInboundPorts: "9443"
    traffic.sidecar.istio.io/excludeOutboundPorts: "9666,6443"

...
```

Check your respective ports set correctly for each component.

### Applying the Annotations

Annotate the KEDA Components: Update the deployment manifests for the KEDA operator, Metrics Adapter, and Admission Webhooks to include the specified pod annotations.

Deploy Updated Manifests: Apply the updated manifests to your Kubernetes cluster.

Verify Communication: Ensure that KEDA components can communicate internally and with external mesh services without failing discovery checks.

### References

For more information on the annotations used, refer to the Istio documentation on traffic management.
Existing troubleshooting guide for KEDA with Istio.

### Conclusion

By applying these annotations, you can ensure that KEDA integrates seamlessly with Istio while adhering to security requirements. This configuration allows KEDA to maintain internal mTLS communication and interact properly with other mesh services.

If you encounter any issues or have further questions, please refer to the KEDA and Istio documentation or reach out to the community for support.

---

> 完整与最新内容以官方文档为准：[KEDA Integration with Istio](https://keda.sh/docs/2.20/integrations/istio-integration/)
