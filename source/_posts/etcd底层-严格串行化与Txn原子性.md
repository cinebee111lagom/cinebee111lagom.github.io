---
title: etcd 底层：严格串行化与 Txn 原子性
date: 2026-09-12 09:18:00
tags:
  - etcd
  - 事务
categories:
  - etcd v3.7 底层细节
---

所有 KV 请求原子：要么全做完要么不做。Watch 侧，一次操作产生的事件落在同一 watch response，不会半截。

无嵌套 Txn：op 执行顺序与列表一致（稳定 GET）。有嵌套 Txn：执行顺序未指定——应用勿依赖未文档化顺序。

Revision 将一次事务多键修改绑在同一逻辑时间点上。

> 延伸阅读：[API guarantees](https://etcd.io/docs/v3.7/learning/api_guarantees/)

