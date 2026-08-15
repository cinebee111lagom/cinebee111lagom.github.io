---
title: etcd v3.7 抓取：Run etcd clusters as a Kubernetes StatefulSet
date: 2026-09-13 09:32:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/op-guide/kubernetes/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/op-guide/kubernetes/>

---

Below demonstrates how to perform the
static bootstrap process
as a Kubernetes StatefulSet.

## Example Manifest

This manifest contains a service and statefulset for deploying a static etcd cluster in kubernetes.

If you copy the contents of the manifest into a file named
etcd.yaml
, it can be applied to a cluster with this command.

etcd.yaml

```
$ kubectl apply --filename etcd.yaml
```

Upon being applied, wait for the pods to become ready.

```
$ kubectl get pods
NAME     READY   STATUS    RESTARTS   AGE
etcd-0   1/1     Running
0
24m
etcd-1   1/1     Running
0
24m
etcd-2   1/1     Running
0
24m
```

The container used in the example includes etcdctl and can be called directly inside the pods.

```
$ kubectl
exec
-it etcd-0 -- etcdctl member list -wtable
+------------------+---------+--------+-------------------------+-------------------------+------------+
|
ID
|
STATUS
|
NAME
|
PEER ADDRS
|
CLIENT ADDRS
|
IS LEARNER
|
+------------------+---------+--------+-------------------------+-------------------------+------------+
|
4f98c3545405a0b0
|
started
|
etcd-2
|
http://etcd-2.etcd:2380
|
http://etcd-2.etcd:2379
|
false
|
|
a394e0ee91773643
|
started
|
etcd-0
|
http://etcd-0.etcd:2380
|
http://etcd-0.etcd:2379
|
false
|
|
d10297b8d2f01265
|
started
|
etcd-1
|
http://etcd-1.etcd:2380
|
http://etcd-1.etcd:2379
|
false
|
+------------------+---------+--------+-------------------------+-------------------------+------------+
```

To deploy with a self-signed certificate, refer to the commented configuration headings starting with
## TLS
to find values that you can uncomment. Additional instructions for generating a cert with cert-manager is included in a section below.

## TLS


> （正文已截断，完整内容见官方链接）

---

> 完整与最新内容以官方文档为准：[Run etcd clusters as a Kubernetes StatefulSet](https://etcd.io/docs/v3.7/op-guide/kubernetes/)
