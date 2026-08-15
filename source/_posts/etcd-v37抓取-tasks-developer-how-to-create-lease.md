---
title: etcd v3.7 抓取：How to create lease
date: 2026-09-13 09:23:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/developer/how-to-create-lease/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/developer/how-to-create-lease/>

---

lease
to write with TTL:

lease

```
etcdctl --endpoints
=
$ENDPOINTS
lease grant
300
# lease 2be7547fbc6a5afa granted with TTL(300s)
etcdctl --endpoints
=
$ENDPOINTS
put sample value --lease
=
2be7547fbc6a5afa
etcdctl --endpoints
=
$ENDPOINTS
get sample
etcdctl --endpoints
=
$ENDPOINTS
lease keep-alive 2be7547fbc6a5afa
etcdctl --endpoints
=
$ENDPOINTS
lease revoke 2be7547fbc6a5afa
# or after 300 seconds
etcdctl --endpoints
=
$ENDPOINTS
get sample
```

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[How to create lease](https://etcd.io/docs/v3.7/tasks/developer/how-to-create-lease/)
