---
title: Dragonfly 参考：Scheduler 命令
date: 2026-09-08 13:10:00
tags:
  - Dragonfly
  - Scheduler
  - 参考
categories:
  - Dragonfly 进阶指南
---

Scheduler 命令行用于启动调度进程。

```shell
scheduler --help
```

确认配置中的服务发现、Redis（若启用）、与 Manager 的连接（若有）。指标端口与 gRPC 端口勿漏防火墙策略。

> 官方文档：[Scheduler commands](https://d7y.io/docs/next/reference/commands/scheduler/)

