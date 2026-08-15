---
title: Dragonfly 概念：Task 任务
date: 2026-09-08 09:00:00
tags:
  - Dragonfly
  - Task
  - 概念
categories:
  - Dragonfly 进阶指南
---

Task 是 Dragonfly 中一次可分发资源的基本单位（文件、镜像等）。可查询、管理与删除。

## 使用方式

| 方式 | 说明 |
|------|------|
| dfget | 命令行下载文件到本地 |
| Web Console | 查看任务详情或删除任务（需 Manager） |

```shell
dfget https://<host>:<port>/<path> -O /tmp/file.txt
```

## 运维含义

- 同一 URL/制品版本应对应稳定 Task，利于缓存命中
- 清理无用 Task 可释放 Peer/Seed 磁盘

> 官方文档：[Task](https://d7y.io/docs/next/concepts/task/)

