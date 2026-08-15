---
title: Dragonfly 参考：dfctl 命令
date: 2026-09-08 13:50:00
tags:
  - Dragonfly
  - dfctl
  - 参考
categories:
  - Dragonfly 进阶指南
---

`dfctl` 常用于轻量部署下的任务预热等控制操作（直连 Scheduler）。

```shell
dfctl task preheat --help
```

K8s 中可在 client Pod 内 exec 执行。是无 Manager 时预热的主路径。

> 官方文档：[dfctl](https://d7y.io/docs/next/reference/commands/client/dfctl/)

