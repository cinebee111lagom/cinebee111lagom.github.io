---
title: etcd 底层：客户端不确定性与重试
date: 2026-09-12 09:19:00
tags:
  - etcd
  - 客户端
categories:
  - etcd v3.7 底层细节
---

超时或网络抖动时，客户端可能不知道写是否已提交（leader 切换也可能让在途请求无 abort 响应）。

## 应用层策略

- 写带幂等键/版本条件（Txn If）
- 超时后用 get/watch 确认
- 区分“可安全重试”与“必须先读”

客户端库的平衡与重试设计见 design-client；不要在未确认时无限盲目重放非幂等写。

> 延伸阅读：[Design client](https://etcd.io/docs/v3.7/learning/design-client/)

