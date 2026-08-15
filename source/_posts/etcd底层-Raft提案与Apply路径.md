---
title: etcd 底层：Raft 提案与 Apply 路径
date: 2026-09-12 09:08:00
tags:
  - etcd
  - Raft
categories:
  - etcd v3.7 底层细节
---

写请求路径（简化）：

```
Client → Leader → Raft Propose → 多数派持久化 → Commit → Apply 到 MVCC → 响应客户端
```

**操作完成**的官方定义：经共识提交并被存储引擎执行（持久化）；客户端收到响应才算自己确认完成。超时/网络中断时客户端可能不确定结果 → 需幂等或读回确认。

Leader 选举期间请求可能被中止，且不一定给客户端 abort 响应。

> 延伸阅读：[API guarantees](https://etcd.io/docs/v3.7/learning/api_guarantees/)

