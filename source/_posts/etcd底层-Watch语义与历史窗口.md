---
title: etcd 底层：Watch 语义与历史窗口
date: 2026-09-12 09:11:00
tags:
  - etcd
  - Watch
categories:
  - etcd v3.7 底层细节
---

Watch 事件保证：

| 保证 | 含义 |
|------|------|
| Ordered | 按 revision 有序，不会先发后到的乱序 |
| Unique | 同一事件不重复投递 |
| Reliable | 历史窗口内 a<b<c 若收到 a、c 则必有 b |
| Atomic | 同一 revision 多键变更不拆开 |
| Resumable | 断线后从上次 revision+1 续订（仍在窗口内） |
| Bookmarkable | Progress 通知保证此前事件已送达 |

健康集群事件延迟常约 ~10ms 量级，但无硬上限；不健康时可能一直收不到。

Txn 无嵌套时，事件顺序与 op 列表一致；有嵌套 TXN 则顺序未指定。

> 延伸阅读：[API guarantees](https://etcd.io/docs/v3.7/learning/api_guarantees/)

