---
title: Dragonfly 抓取：Upgrade
date: 2026-09-14 09:31:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/operations/integrations/upgrade/>

---

## Upgrade the cluster deployed by Helm

User can deploy a dragonfly cluster on kubernetes with Helm.
The
helm chart
is a project managed by dragonfly Team.
User can query and download the latest version chart or history version
from
Artifact Hub
.

Before Upgrade, user must read the
Change Log
to
make sure the breaking changes between the current version and target version.

```
# check the dragonfly repo existence
helm repo list | grep dragonfly
# [Optional] add repo if not exist
helm repo add dragonfly https://dragonflyoss.github.io/helm-charts/
# update locally cached repo information
helm repo update
# upgrade the dragonfly
helm upgrade --install -n dragonfly-system dragonfly dragonfly/dragonfly [--version 0.5.50] [-f values.yaml]
```

Note:

On the above example,
dragonfly/dragonfly
means
dragonfly
release under
dragonfly
repo,
0.5.50
is the upgrading target version，user can specify the version as you want.

If user need specify extra parameters, user can edit the
values.yaml
you configured for the old release and
specify with
-f values.yaml
.

If you want to drop the chart parameters you configured for the old release or set some new parameters,
it is recommended to add
--reset-values
flag in helm upgrade command.

When upgrading, If you want to reuse the last release's values, it is recommended to add
--reuse-values
flag
in helm upgrade command.

More information about
helm upgrade
sub-command
can be found in
helm home page
.

For those users can't fetch the chart from remote repo, follow this step:
# download dragonfly helm chart from github source repo. use version 0.5.50 as an example
# method 1：
wget https://github.com/dragonflyoss/helm-charts/releases/download/dragonfly-0.5.50/dragonfly-0.5.50.tgz
# method 2：
git clone -b dragonfly-0.5.50 --depth=1  https://github.com/dragonflyoss/helm-charts.git
# upgrade the dragonfly
helm upgrade --install -n dragonfly-system dragonfly <Path/To/Chart> [-f values.yaml | --reset-values]

For those users can't fetch the chart from remote repo, follow this step:

```
# download dragonfly helm chart from github source repo. use version 0.5.50 as an example
# method 1：
wget https://github.com/dragonflyoss/helm-charts/releases/download/dragonfly-0.5.50/dragonfly-0.5.50.tgz
# method 2：
git clone -b dragonfly-0.5.50 --depth=1  https://github.com/dragonflyoss/helm-charts.git
# upgrade the dragonfly
helm upgrade --install -n dragonfly-system dragonfly <Path/To/Chart> [-f values.yaml | --reset-values]
```

---

> 完整与最新内容以官方文档为准：[Upgrade](https://d7y.io/docs/next/operations/integrations/upgrade/)
