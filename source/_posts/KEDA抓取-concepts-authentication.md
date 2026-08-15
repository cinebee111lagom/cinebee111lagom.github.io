---
title: KEDA 抓取：Authentication
date: 2026-09-14 09:13:00
tags:
  - KEDA
  - 抓取
  - 文档
categories:
  - KEDA 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://keda.sh/docs/2.20/concepts/authentication/>

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

Authentication
Latest

Often a scaler will require authentication or secrets and config to check for events.

KEDA provides a few secure patterns to manage authentication flows:

Configure authentication per
ScaledObject

Re-use per-namespace credentials or delegate authentication with
TriggerAuthentication

Re-use global credentials with
ClusterTriggerAuthentication

## Defining secrets and config maps on ScaledObject

Some metadata parameters will not allow resolving from a literal value, and will instead require a reference to a secret, config map, or environment variable defined on the target container.

💡
TIP:
If creating a deployment yaml that references a secret, be sure the secret is created before the deployment that references it, and the scaledObject after both of them to avoid invalid references.

### Example

If using the
RabbitMQ scaler
, the
host
parameter may include passwords so is required to be a reference. You can create a secret with the value of the
host
string, reference that secret in the deployment, and map it to the
ScaledObject
metadata parameter like below:

```
apiVersion
: v1
kind
: Secret
metadata
:
name
: {secret-name}
data
:
{
secret-key-name}
: YW1xcDovL3VzZXI6UEFTU1dPUkRAcmFiYml0bXEuZGVmYXVsdC5zdmMuY2x1c3Rlci5sb2NhbDo1Njcy
#base64 encoded per secret spec
---
apiVersion
: apps/v1
kind
: Deployment
metadata
:
name
: {deployment-name}
namespace
: default
labels
:
app
: {deployment-name}
spec
:
selector
:
matchLabels
:
app
: {deployment-name}
template
:
metadata
:
labels
:
app
: {deployment-name}
spec
:
containers
:
-
name
: {deployment-name}
image
: {container-image}
envFrom
:
-
secretRef
:
name
: {secret-name}
---
apiVersion
: keda.sh/v1alpha1
kind
: ScaledObject
metadata
:
name
: {scaled-object-name}
namespace
: default
spec
:
scaleTargetRef
:
name
: {deployment-name}
triggers
:
-
type
: rabbitmq
metadata
:
queueName
: hello
host
: {secret-key-name}
queueLength
:
'5'
```

If you have multiple containers in a deployment, you will need to include the name of the container that has the references in the
ScaledObject
. If you do not include a
envSourceContainerName
it will default to the first container. KEDA will attempt to resolve references from secrets, config maps, and environment variables of the container.

### The downsides

While this method works for many scenarios, there are some downsides:

Difficult to efficiently share auth
config across
ScaledObjects

No support for referencing a secret directly
, only secrets that are referenced by the container

No support for other types of authentication flows
such as
pod identity
where access to a source could be acquired with no secrets or connection strings

For these and other reasons, we also provide a
TriggerAuthentication
resource to define authentication as a separate resource to a
ScaledObject
. This allows you to reference secrets directly, configure to use pod identity or use authentication object managed by a different team.

## Re-use credentials and delegate auth with TriggerAuthentication

TriggerAuthentication
allows you to describe authentication parameters separate from the
ScaledObject
and the deployment containers. It also enables more advanced methods of authentication like “pod identity”, authentication re-use or allowing IT to configure the authentication.

```
apiVersion
: keda.sh/v1alpha1
kind
: TriggerAuthentication
metadata
:
name
: {trigger-authentication-name}
namespace
: default
# must be same namespace as the ScaledObject
spec
:
podIdentity
:
provider
: none | azure-workload | aws | aws-eks | gcp
# Optional. Default: none
identityId
: <identity-id>
# Optional. Only used by azure & azure-workload providers.
roleArn
: <role-arn>
# Optional. Only used by aws provider.
identityOwner
: keda|workload
# Optional. Only used by aws provider.
secretTargetRef
:
# Optional.
-
parameter
: {scaledObject-parameter-name}
# Required.
name
: {secret-name}
# Required.
key
: {secret-key-name}
# Required.
env
:
# Optional.
-
parameter
: {scaledObject-parameter-name}
# Required.
name
: {env-name}
# Required.
containerName
: {container-name}
# Optional. Default: scaleTargetRef.envSourceContainerName of ScaledObject
filePath
:
# Optional. Define only for ClusterTriggerAuthentication; not supported for TriggerAuthentication.
-
parameter
: {scaledObject-parameter-name}
# Required.
path
: {relative-path-to-file}
# Required. Relative to --filepath-auth-root-path.
hashiCorpVault
:
# Optional.
address
: {hashicorp-vault-address}
# Required.
namespace
: {hashicorp-vault-namespace}
# Optional. Default is root namespace. Useful for Vault Enterprise
authentication
: token | kubernetes
# Required.
role
: {hashicorp-vault-role}
# Optional.
mount
: {hashicorp-vault-mount}
# Optional.
credential
:
# Optional.
token
: {hashicorp-vault-token}
# Optional.
serviceAccount
: {path-to-service-account-file}
# Optional.
secrets
:
# Required.
-
parameter
: {scaledObject-parameter-name}
# Required.
key
: {hashicorp-vault-secret-key-name}
# Required.
path
: {hashicorp-vault-secret-path}
# Required.
azureKeyVault
:
# Optional.
vaultUri
: {key-vault-address}
# Required.
podIdentity
:
# Optional. Required when using pod identity.
provider
: azure-workload
# Required.
identityId
: <identity-id>
# Optional
credentials
:
# Optional. Required when not using pod identity.
clientId
: {azure-ad-client-id}
# Required.
clientSecret
:
# Required.
valueFrom
:
# Required.
secretKeyRef
:
# Required.
name
: {k8s-secret-with-azure-ad-secret}
# Required.
key
: {key-within-the-secret}
# Required.
tenantId
: {azure-ad-tenant-id}
# Required.
cloud
:
# Optional.
type
: AzurePublicCloud | AzureUSGovernmentCloud | AzureChinaCloud | AzureGermanCloud | Private
# Required.
keyVaultResourceURL
: {key-vault-resource-url-for-cloud}
# Required when type = Private.
activeDirectoryEndpoint
: {active-directory-endpoint-for-cloud}
# Required when type = Private.
secrets
:
# Required.
-
parameter
: {param-name-used-for-auth}
# Required.
name
: {key-vault-secret-name}
# Required.
version
: {key-vault-secret-version}
# Optional.
awsSecretManager
:
podIdentity
:
# Optional.
provider
: aws
# Required.
credentials
:
# Optional.
accessKey
:
# Required.
valueFrom
:
# Required.
secretKeyRef
:
# Required.
name
: {k8s-secret-with-aws-credentials}
# Required.
key
: AWS_ACCESS_KEY_ID
# Required.
accessSecretKey
:
# Required.
valueFrom
:
# Required.
secretKeyRef
:
# Required.
name
: {k8s-secret-with-aws-credentials}
# Required.
key
: AWS_SECRET_ACCESS_KEY
# Required.
region
: {aws-region}
# Optional.
secrets
:
# Required.
-
parameter
: {param-name-used-for-auth}
# Required.
name
: {aws-secret-name}
# Required.
version
: {aws-secret-version}
# Optional.
secretKey
: {aws-secret-key}
# Optional.
gcpSecretManager
:
# Optional.
secrets
:
# Required.
-
parameter
: {param-name-used-for-auth}
# Required.
id
: {secret-manager-secret-name}
# Required.
version
: {secret-manager-secret-name}
# Optional.
podIdentity
:
# Optional.
provider
: gcp
# Required.
credentials
:
# Optional.
clientSecret
:
# Required.
valueFrom
:
# Required.
secretKeyRef
:
# Required.
name
: {k8s-secret-with-gcp-iam-sa-secret}
# Required.
key
: {key-within-the-secret}
# Required.
```

Based on the requirements you can mix and match the reference types providers in order to configure all required parameters.

Every parameter you define in
TriggerAuthentication
definition does not need to be included in the
metadata
of the trigger for your
ScaledObject
definition. To reference a
TriggerAuthentication
from a
ScaledObject
you add the
authenticationRef
to the trigger.

```
# some Scaled Object
# ...
triggers
:
-
type
: {scaler-type}
metadata
:
param1
: {some-value}
authenticationRef
:
name
: {trigger-authentication-name}
# this may define other params not defined in metadata
```

## Authentication scopes: Namespace vs. Cluster

Each
TriggerAuthentication
is defined in one namespace and can only be used by a
ScaledObject
in that same namespace. For cases where you want to share a single set of credentials between scalers in many namespaces, you can instead create a
ClusterTriggerAuthentication
. As a global object, this can be used from any namespace. To set a trigger to use a
ClusterTriggerAuthentication
, add a
kind
field to the authentication reference:

```
authenticationRef
:
name
: {cluster-trigger-authentication-name}
kind
: ClusterTriggerAuthentication
```

By default, Secrets loaded from a
secretTargetRef
must be in the same namespace as KEDA is deployed in (usually
keda
). This can be overridden by setting a
KEDA_CLUSTER_OBJECT_NAMESPACE
environment variable for the
keda-operator
container.

Defining a
ClusterTriggerAuthentication
works almost identically to a
TriggerAuthentication
, except there is no
metadata.namespace
value:

```
apiVersion
: keda.sh/v1alpha1
kind
: ClusterTriggerAuthentication
metadata
:
name
: {cluster-trigger-authentication-name}
spec
:
# As before ...
```

## Authentication parameters

Authentication parameters can be pulled in from many sources. All of these values are merged together to make the authentication data for the scaler. You can find the all the available authentications
here
.

### Environment variable(s)

You can pull information via one or more environment variables by providing the
name
of the variable for a given
containerName
.

```
env
:
# Optional.
-
parameter
: region
# Required - Defined by the scale trigger
name
: my-env-var
# Required.
containerName
: my-container
# Optional. Default: scaleTargetRef.envSourceContainerName of ScaledObject
```

Assumptions:
containerName
is in the same resource as referenced by
scaleTargetRef.name
in the ScaledObject, unless specified otherwise.

### Secret(s)

You can pull one or more secrets into the trigger by defining the
name
of the Kubernetes Secret and the
key
to use.


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Authentication](https://keda.sh/docs/2.20/concepts/authentication/)
