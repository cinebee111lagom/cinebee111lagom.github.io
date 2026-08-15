---
title: etcd v3.7 文档：如何处理成员变更
date: 2026-09-11 09:15:00
tags:
  - etcd
  - 成员
categories:
  - etcd v3.7 文档导读
---

member add/remove/update 的正确顺序与注意事项。一次只变一个成员，变更后检查健康与数据同步。

> 官方文档（v3.7）：[etcd v3.7 文档：如何处理成员变更](https://etcd.io/docs/v3.7/tasks/operator/how-to-deal-with-membership/)

