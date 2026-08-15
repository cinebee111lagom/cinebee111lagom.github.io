---
title: Dragonfly 常见问题 FAQ
date: 2026-09-08 16:10:00
tags:
  - Dragonfly
  - FAQ
  - 排障
categories:
  - Dragonfly 进阶指南
---

## 动态调整日志级别

向进程发送 `SIGUSR1` 循环切换日志级别：

```shell
kill -s SIGUSR1 <pid of dfdaemon, scheduler or manager>
```

事件出现在 stdout / `core.log`（高于 info 时可能仅 stdout）。

## 500 Internal Server Error

1. 查看 `/var/log/dragonfly/dfdaemon/` 错误日志
2. 检查源站连通性（DNS、证书）

```shell
curl https://example.harbor.local/
```

curl 失败则先修源站/证书再查 P2P。

> 官方文档：[FAQ](https://d7y.io/docs/next/faq/)

