---
title: Dragonfly 抓取：Preheat
date: 2026-09-14 09:43:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/advanced-guides/open-api/preheat/>

---

This document will help you experience how to use Dragonfly's Open API for preheating.

## Create personal access token

Click the
ADD PERSONAL ACCESS TOKENS
button to create personal access token.

Name
: Set your token a descriptive name.

Description
: Set a description.

Expiration
: Set your token an expiration.

Scopes
: Select the access permissions for the token.

Click
SAVE
and copy the token and store it. For your security, it doesn't display again.

## Preheat image

Use Open API for preheating image. First create a POST request for preheating.

args
: Parameters for the preheat job.

url
: URL used to specify the resource to be preheated.

concurrent_task_count
: Used to specify the maximum number of tasks (e.g., image layers) to preheat concurrently.
For example, if preheating 100 layers with ConcurrentTaskCount set to 10, up to 10 layers are processed simultaneously.
If ConcurrentPeerCount is 10 for 1000 peers, each layer is preheated by 10 peers concurrently.Default is 8, maximum is 100.

concurrent_peer_count
: Used to specify the maximum number of peers to preheat concurrently for a single task (e.g., an image layer).
For example, if preheating a layer with ConcurrentPeerCount set to 10, up to 10 peers process that layer simultaneously.
Default is 500, maximum is 1000.

platform
: The image type preheating task can specify the image architecture type. eg: linux/amd64、linux/arm64.

scope
: Select the scope of preheat as needed.
single_seed_peer
: Preheat to a seed peer.
all_seed_peers
: Preheat to each seed peer in the P2P cluster.
count
: The count of preheat seed peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.
percentage
: The percentage of preheat seed peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.
ips
: By setting the IPs, can specify a seed peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.
all_peers
: Preheat to each peer in the P2P cluster.
count
: The count of preheat peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.
percentage
: The percentage of preheat peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.
ips
: By setting the IPs, can specify a peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.

scope
: Select the scope of preheat as needed.

single_seed_peer
: Preheat to a seed peer.

all_seed_peers
: Preheat to each seed peer in the P2P cluster.
count
: The count of preheat seed peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.
percentage
: The percentage of preheat seed peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.
ips
: By setting the IPs, can specify a seed peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.

all_seed_peers
: Preheat to each seed peer in the P2P cluster.

count
: The count of preheat seed peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.

percentage
: The percentage of preheat seed peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.

ips
: By setting the IPs, can specify a seed peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.

all_peers
: Preheat to each peer in the P2P cluster.
count
: The count of preheat peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.
percentage
: The percentage of preheat peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.
ips
: By setting the IPs, can specify a peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.

all_peers
: Preheat to each peer in the P2P cluster.

count
: The count of preheat peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.

percentage
: The percentage of preheat peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.

ips
: By setting the IPs, can specify a peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.

username
: The username used to authenticate the image manifest.

password
: The password used to authenticate the image manifest.

tag
: When the URL of the preheat task are the same but the Tag are different, they will be distinguished based on the
tag and the generated preheat task will be different.

application
: When the URL of the preheat tasks are the same but the application are different, they will be distinguished based on the application and the generated preheat tasks will be different.

filtered_query_params
: By setting the filter parameter, you can specify the file type of the resource that needs to be preheated. The filter is used to generate a unique preheat task and filter unnecessary query parameters in the URL, separated by & characters.

headers
: Add headers for preheat requests.

scheduler_cluster_ids:
Specify the preheated scheduler cluster id,
if
scheduler_cluster_ids
is empty, it means preheating all scheduler clusters.

```
curl --location --request POST 'http://dragonfly-manager:8080/oapi/v1/jobs' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer your_dragonfly_personal_access_token' \
--data-raw '{
"type": "preheat",
"args": {
"type": "image",
"url": "https://index.docker.io/v2/library/alpine/manifests/3.19",
"username": "your_registry_username",
"password": "your_registry_password",
"scope": "single_seed_peer"
},
"scheduler_cluster_ids":[1]
}'
```

The command-line log returns the preheat job id.

```
{
"id": 1,
"created_at": "0001-01-01T00:00:00Z",
"updated_at": "0001-01-01T00:00:00Z",
"task_id": "group_9523f30a-877d-41f7-a25f-0854228341f6",
"type": "preheat",
"state": "PENDING",
"args": {
"scope": "single_seed_peer",
"type": "image",
"url": "https://dockerpull.org/v2/library/alpine/manifests/3.19"
},
"result": null,
"scheduler_clusters": [
{
"id": 1,
"created_at": "2024-12-11T07:57:44Z",
"updated_at": "2024-12-11T07:57:44Z",
"name": "cluster-1"
}
]
}
```

Polling the preheating status with job id.

```
curl --request GET 'http://dragonfly-manager:8080/oapi/v1/jobs/1' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer your_dragonfly_personal_access_token'
```

If the status is
SUCCESS
, the preheating is successful.

```
{
"id": 1,
"created_at": "0001-01-01T00:00:00Z",
"updated_at": "0001-01-01T00:00:00Z",
"task_id": "group_9523f30a-877d-41f7-a25f-0854228341f6",
"type": "preheat",
"state": "SUCCESS",
"args": {
"scope": "single_seed_peer",
"type": "image",
"url": "https://dockerpull.org/v2/library/alpine/manifests/3.19"
},
"result": null,
"scheduler_clusters": [
{
"id": 1,
"created_at": "2024-12-11T07:57:44Z",
"updated_at": "2024-12-11T07:57:44Z",
"name": "cluster-1"
}
]
}
```

## Preheat file

Use Open API for preheating file. First create a POST request for preheating.

args
: Parameters for the preheat job.

urls
: Used to specify the URL addresses of resources requiring preheating, supporting multiple URLs in a single preheat request.

concurrent_task_count
: Used to specify the maximum number of tasks (e.g., image layers) to preheat concurrently.
For example, if preheating 100 layers with ConcurrentTaskCount set to 10, up to 10 layers are processed simultaneously.
If ConcurrentPeerCount is 10 for 1000 peers, each layer is preheated by 10 peers concurrently.Default is 8, maximum is 100.

concurrent_peer_count
: Used to specify the maximum number of peers to preheat concurrently for a single task (e.g., an image layer).
For example, if preheating a layer with ConcurrentPeerCount set to 10, up to 10 peers process that layer simultaneously.
Default is 500, maximum is 1000.

scope
: Select the scope of preheat as needed.
single_seed_peer
: Preheat to a seed peer.
all_seed_peers
: Preheat to each seed peer in the P2P cluster.
count
: The count of preheat seed peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.
percentage
: The percentage of preheat seed peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.
ips
: By setting the IPs, can specify a peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.
all_peers
: Preheat to each peer in the P2P cluster.
count
: The count of preheat peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.
percentage
: The percentage of preheat peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.
ips
: By setting the IPs, can specify a seed peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.

scope
: Select the scope of preheat as needed.

single_seed_peer
: Preheat to a seed peer.

all_seed_peers
: Preheat to each seed peer in the P2P cluster.
count
: The count of preheat seed peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.
percentage
: The percentage of preheat seed peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.
ips
: By setting the IPs, can specify a peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.

all_seed_peers
: Preheat to each seed peer in the P2P cluster.

count
: The count of preheat seed peers desired.
This field is used only when
IPs
is not specified. It has priority over
Percentage
.
It must be a value between 1 and 200 (inclusive) if provided.

percentage
: The percentage of preheat seed peers desired.
This field has the lowest priority and is only used if both
IPs
and
Count
are not provided.
It must be a value between 1 and 100 (inclusive) if provided.

ips
: By setting the IPs, can specify a peer IP for preheating. This field has the highest priority: if provided, both
Count
and
Percentage
will be ignored.


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Preheat](https://d7y.io/docs/next/advanced-guides/open-api/preheat/)
