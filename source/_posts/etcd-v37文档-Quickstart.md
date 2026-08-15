---
title: etcd v3.7 文档：Quickstart
date: 2026-09-11 09:01:00
tags:
  - etcd
  - 入门
categories:
  - etcd v3.7 文档导读
---

五分钟本地单节点：

1. 安装并确保 `etcd` 在 PATH  
2. 终端运行 `etcd`  
3. 另一终端：

```bash
etcdctl put greeting "Hello, etcd"
etcdctl get greeting
```

下一步：开发者看 API/语言绑定；运维看多机集群、TLS、tuning。

> 官方文档（v3.7）：[etcd v3.7 文档：Quickstart](https://etcd.io/docs/v3.7/quickstart/)

