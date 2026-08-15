---
title: etcd 底层：Compaction 压缩机制
date: 2026-09-12 09:06:00
tags:
  - etcd
  - Compaction
categories:
  - etcd v3.7 底层细节
---

若不压缩，多版本历史无限增长。Compaction 丢掉 **compact revision 之前** 的旧版本，保留足够窗口给 Watch/历史读。

## 运维含义

- 自动压缩（如 Kubernetes 侧配置）必须开启且周期合理
- 压缩过猛：Watch 从旧 revision 续订会失败（历史窗口外）
- 压缩过缓：db 变大、内存索引膨胀、性能变差

压缩 ≠ defrag：压缩删逻辑历史；defrag 整理后端碎片空间。

> 延伸阅读：[Maintenance](https://etcd.io/docs/v3.7/op-guide/maintenance/)

