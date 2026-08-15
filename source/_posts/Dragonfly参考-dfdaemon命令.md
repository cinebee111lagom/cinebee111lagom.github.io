---
title: Dragonfly 参考：dfdaemon 命令
date: 2026-09-08 13:30:00
tags:
  - Dragonfly
  - dfdaemon
  - 参考
categories:
  - Dragonfly 进阶指南
---

`dfdaemon` 是 Peer/Seed 守护进程，提供下载、上传、Proxy 等。

```shell
dfdaemon --help
```

生产以 systemd/K8s 托管；关注配置文件、数据目录、代理端口与 Seed 模式开关。

> 官方文档：[dfdaemon](https://d7y.io/docs/next/reference/commands/client/dfdaemon/)

