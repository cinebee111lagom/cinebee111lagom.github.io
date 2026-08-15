---
title: Dragonfly 抓取：Task
date: 2026-09-14 09:53:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/advanced-guides/web-console/resource/task/>

---

In this article, you will be shown Task page information.

## Search Task

### Search by URL

URL
: Query the task cache based on the URL.

Piece Length
: When the task URLs are the same but the Piece Length is different,
they will be distinguished based on the Piece Length, and the queried tasks will also be different.

Tag
: When the task URL is the same but the tags are different,
they will be distinguished based on the tags, and the queried tasks will also be different.

Application
: Caller application which is used for statistics and access control.

Filter Query Params
: Filter the query parameters of the downloaded URL.
If the download URL is the same, it will be scheduled as the same task.

### Search by Image Manifest URL

Deletion of the image manifest URL task cache is not supported yet.

Image Manifest URL
: Query the task cache based on the image manifest URL.

### Search by Task ID

Task ID
: Query the task cache based on the task id.

### Search by Content for Calculating Task ID

Content for Calculating Task ID
: Query the task cache based on the content for calculating task id.

## Delete task

Click
DELETE
and delete task.

The deleted task will not return results immediately and you need to wait.

## Executions

Displays all deleted task.

## Execution

If the status is SUCCESS and the Failure list does not exist, it means that the deletion task is successful.

## Execution failed

The Failure list will show the tasks that failed to execute.

Click the
Description
icon to view the failure log.

---

> 完整与最新内容以官方文档为准：[Task](https://d7y.io/docs/next/advanced-guides/web-console/resource/task/)
