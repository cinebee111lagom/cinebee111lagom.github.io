---
title: Volcano 抓取：CLI
date: 2026-09-14 10:06:00
tags:
  - Volcano
  - 抓取
  - 文档
categories:
  - Volcano 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://volcano.sh/zh-Hans/docs/CLI/Commandline>

---

### 简介

Volcano提供了命令行工具用于管理资源。

## 配置

您可以自己从 github 上克隆代码并在项目的根目录下执行以下命令制作最新的可执行文件：

```
# make vcctl
```

将可执行文件拷贝到$PATH下以便您能在任何地方执行它。

## 命令行列表

### 列举所有的Job

```
# vcctl job list
Name    Creation       Phase       JobType     Replicas    Min   Pending   Running   Succeeded   Failed    Unknown     RetryCount
job-1   2020-09-01     Running     Batch       1           1     0         1         0           0         0           0
```

### 删除指定的Job

```
# vcctl delete job --name job-1 --namespaces default
delete job job-1 successfully
```

### 中止一个Job

```
# vcctl job suspend --name job-1 --namespace default
```

### 消费一个Job (与"vcctl job suspend"相反)

```
# vcctl job resume --name job-1 --namespace default
```

### 运行一个Job

```
# vcctl job run --name job-1 --namespace default
```

## 说明事项

如需获取更多命令行详情请按如下操作:

```
# vcctl -h
# vcctl [command] -h
```

---

> 完整与最新内容以官方文档为准：[CLI](https://volcano.sh/zh-Hans/docs/CLI/Commandline)
