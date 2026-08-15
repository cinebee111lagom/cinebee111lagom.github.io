---
title: etcd 底层：Peer 流量优先于 Client
date: 2026-09-12 09:14:00
tags:
  - etcd
  - 网络
categories:
  - etcd v3.7 底层细节
---

Leader 客户端请求过多时，可能挤压 peer 消息，Follower 出现：

```text
dropped MsgProp ... sending buffer is full
dropped MsgAppResp ... sending buffer is full
```

Linux 可用 tc 把 **2380 peer** 端口优先级置于 **2379 client** 之上，保证共识通道。

本质：共识流量是集群生命线，客户端流量可限流/分片，不可反客为主。

> 延伸阅读：[Tuning](https://etcd.io/docs/v3.7/tuning/)

