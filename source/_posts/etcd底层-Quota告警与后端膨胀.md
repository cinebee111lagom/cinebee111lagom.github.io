---
title: etcd 底层：Quota、告警与后端膨胀
date: 2026-09-12 09:16:00
tags:
  - etcd
  - Quota
categories:
  - etcd v3.7 底层细节
---

`--quota-backend-bytes` 限制 db 大小。触及配额会触发 **NOSPACE** 类告警，写入失败，直到压缩+整理并解除告警。

## 链条

```
写入多 / 压缩不足 → db 涨 → 触配额 → 写失败
                 → compaction → defrag → disalarm
```

监控 db 大小、配额使用率、告警状态，比等应用报错再查更早。

> 延伸阅读：[Maintenance](https://etcd.io/docs/v3.7/op-guide/maintenance/)

