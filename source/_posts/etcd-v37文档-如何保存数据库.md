---
title: etcd v3.7 文档：如何保存数据库（快照）
date: 2026-09-11 09:14:00
tags:
  - etcd
  - 备份
categories:
  - etcd v3.7 文档导读
---

定期 `etcdctl snapshot save`，校验快照，异地存放。恢复走 snapshot restore 流程（见 disaster recovery）。

> 官方文档（v3.7）：[etcd v3.7 文档：如何保存数据库（快照）](https://etcd.io/docs/v3.7/tasks/operator/how-to-save-database/)

