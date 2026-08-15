---
title: etcd 底层：Revision 逻辑时钟
date: 2026-09-12 09:02:00
tags:
  - etcd
  - Revision
categories:
  - etcd v3.7 底层细节
---

集群创建时 revision 从 **1** 起。每次原子变更（一次 Txn 即使含多 op 也只占 **一个** revision）使键空间推进到新 revision；旧 revision 数据不变。

## 要点

| 点 | 说明 |
|----|------|
| 单调递增 | 集群生命周期内 revision 只增 |
| 逻辑时钟 | 更大 revision = 更晚修改 |
| 同 revision | 同一操作“并发”改动的多键 |
| 压缩 | compact 之后，更早 revision 不可再访问 |

Watch 按 revision 排序；客户端断线续订也应带上次收到的 revision。

> 延伸阅读：[API guarantees](https://etcd.io/docs/v3.7/learning/api_guarantees/)

