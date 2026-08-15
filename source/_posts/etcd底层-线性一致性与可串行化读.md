---
title: etcd 底层：线性一致性与可串行化读
date: 2026-09-12 09:10:00
tags:
  - etcd
  - 一致性
categories:
  - etcd v3.7 底层细节
---

KV API 默认提供 **durability + strict serializability**（强隔离）。

## Linearizable 读

读也走共识路径，保证读到“不早于调用时刻”的最新已提交值，但延迟更高。

## Serializable 读

可配置为可串行化读：可能读到相对 quorum 的旧数据，但吞吐更好、延迟更低。

Watch **不保证** linearizability；要用事件里的 revision 与其它操作对齐。

Strict serializability ⇒ 原子性 +（默认）线性一致性等更易推理的性质。

> 延伸阅读：[API guarantees](https://etcd.io/docs/v3.7/learning/api_guarantees/)

