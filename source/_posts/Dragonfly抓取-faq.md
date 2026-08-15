---
title: Dragonfly 抓取：FAQ
date: 2026-09-14 10:18:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/faq/>

---

## Change log level

Send
SIGUSR1
signal to dragonfly process to change log level

```
kill -s SIGUSR1 <pid of dfdaemon, scheduler or manager>
```

stdout:

```
change log level to debug
change log level to fatal
change log level to panic
change log level to dpanic
change log level to error
change log level to warn
change log level to info
```

The change log level event will print in stdout and
core.log
file, but if the level is greater than
info
, stdout only.

## 500 Internal Server Error

1.
Check error logs in /var/log/dragonfly/dfdaemon/

2.
Check source connectivity(dns error or certificate error)

Example:

```
curl https://example.harbor.local/
```

When curl says error, please check the details in output.

---

> 完整与最新内容以官方文档为准：[FAQ](https://d7y.io/docs/next/faq/)
