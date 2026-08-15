---
title: etcd 底层：Lease 与分布式协调
date: 2026-09-12 09:12:00
tags:
  - etcd
  - Lease
categories:
  - etcd v3.7 底层细节
---

Lease：grant → put 绑键 → keepalive → revoke / TTL 到期。

## 实现锁时必须知道的

- 锁的正确性依赖租约过期与 **fencing**（持锁者带世代号），不能假设“我以为还持有”
- keepalive 失败要按过期处理
- 大量短租约会增加心跳与存储压力

Lease API 本身简单，但分布式锁/选主的正确用法要读 concurrency 相关文档与客户端实现。

> 延伸阅读：[API guarantees](https://etcd.io/docs/v3.7/learning/api_guarantees/)

