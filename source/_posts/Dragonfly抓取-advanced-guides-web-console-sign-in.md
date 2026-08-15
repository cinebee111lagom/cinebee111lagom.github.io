---
title: Dragonfly 抓取：Sign in
date: 2026-09-14 09:46:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/advanced-guides/web-console/sign-in/>

---

The default username and password are
root
and
dragonfly
.

Note: It is strongly recommended that you change the default administrator password.

## Customize the initial root password

Set the
DRAGONFLY_INITIAL_ROOT_PASSWORD
environment variable of the manager to seed the root user
with a custom password instead of the default one. The password must be between 8 and 20 characters.

If you deploy Dragonfly with
Helm Charts
, set it through
manager.extraEnvVars
, preferably referencing a Kubernetes secret:

```
manager
:
extraEnvVars
:
-
name
:
DRAGONFLY_INITIAL_ROOT_PASSWORD
valueFrom
:
secretKeyRef
:
name
:
dragonfly
-
root
-
password
key
:
password
```

Note: The environment variable only takes effect when the root user is created for the first time.
After that, the password is managed in the database and can be changed from the console.

---

> 完整与最新内容以官方文档为准：[Sign in](https://d7y.io/docs/next/advanced-guides/web-console/sign-in/)
