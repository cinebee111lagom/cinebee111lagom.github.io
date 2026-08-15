---
title: Dragonfly 抓取：Cluster
date: 2026-09-14 09:49:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/advanced-guides/web-console/cluster/>

---

In this article, you will be shown Cluster page information.

## Clusters

When you sign in successfully, you will come to the clusters list page, which will display all of the clusters information.

## Cluster

Display the cluster details, each attribute has prompt information on the button
?
.

## Create Cluster

Create a cluster, and at the same time create a set of scheduler cluster and seed peer cluster with
1:1
relationship.
A Cluster can represent a P2P cluster, including a scheduler cluster and a seed peer cluster.

### Information

The information of cluster.

Set cluster as your default cluster
: When peer does not find a matching cluster based on scopes,
the default cluster will be used.

### Scopes

The cluster needs to serve the scope. It will provide scheduler services and seed peer services to peers in the scope.

Location
: The cluster needs to serve all peers in the location. When the location in the peer configuration matches
the location in the cluster, the peer will preferentially use the scheduler and the seed peer of the cluster.
It separated by "|", for example "area|country|province|city".

IDC
: The cluster needs to serve all peers in the IDC. When the IDC in the peer configuration matches the IDC in the cluster,
the peer will preferentially use the scheduler and the seed peer of the cluster.
IDC has higher priority than location in the scopes.

CIDRs
: The cluster needs to serve all peers in the CIDRs. The advertise IP will be reported in the peer
configuration when the peer is started, and if the advertise IP is empty in the peer configuration,
peer will automatically get expose IP as advertise IP. When advertise IP of the peer matches the CIDRs in cluster,
the peer will preferentially use the scheduler and the seed peer of the cluster.
CIDRs has higher priority than IDC in the scopes.

Hostnames
: The cluster needs to serve all peers in Hostname. The input parameter is the multiple Hostname regexes.
The Hostname will be reported in the peer configuration when the peer is started.
When the Hostname matches the multiple Hostname regexes in the cluster,
the peer will preferentially use the scheduler and the seed peer of the cluster.
Hostname has higher priority than IDC in the scopes.Hostname has priority equal to CIDRs in the scopes.

### Config

The configuration for P2P downloads.

Seed Peer load limit
: Int If other peers download from the seed peer, the load of the seed peer will increase.
When the load limit of the seed peer is reached, the scheduler will no longer schedule other peers to
download from the seed peer until the it has the free load.

Peer load limit
: If other peers download from the peer, the load of the peer will increase.
When the load limit of the peer is reached, the scheduler will no longer schedule other peers to
download from the peer until the it has the free load.

Candidate parent limit
: The maximum number of parents that the scheduler can schedule for download peer.

Filter parent limit
: The scheduler will randomly select the number of parents from all the parents according to
the filter parent limit and evaluate the optimal parents in selecting parents for the peer to download task.
The number of optimal parent is the scheduling parent limit.

Job Rate Limit(requests per seconds)
: The rate limit(requests per second) for job Open API, default value is 10.

## Update Cluster

Update cluster information.

## Delete Cluster

Delete cluster and at the same time delete scheduler cluster and seed peer cluster.

## Schedulers

Display the schedulers.

## Scheduler

Display the scheduler details.

## Delete Scheduler

Delete scheduler record in database.

## Delete all inative instances

Delete inactive schedulers record in database.

## Seed Peer

Display the seed peer details.

## Delete seed peer

Delete seed peer record in database.

## Delete all inative instances

Delete inactive seed peers record in database.

## Peers

Display the peer information, You can click the
?
button to display prompt information.

Note: peer data is T+1.

## Refresh Peer Date

Force refresh of peer data.

## Export Peer Date

Export the peer data.

---

> 完整与最新内容以官方文档为准：[Cluster](https://d7y.io/docs/next/advanced-guides/web-console/cluster/)
