---
title: Dragonfly 参考：dfget 命令
date: 2026-09-08 13:20:00
tags:
  - Dragonfly
  - dfget
  - 参考
categories:
  - Dragonfly 进阶指南
---

`dfget` 是客户端下载工具，经 dfdaemon/gRPC 拉取文件。

```shell
dfget https://example.com/file -O /tmp/file
dfget --help
```

适合脚本与人工验证 P2P 是否生效。

> 官方文档：[dfget](https://d7y.io/docs/next/reference/commands/client/dfget/)

