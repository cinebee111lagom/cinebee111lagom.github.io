---
title: Dragonfly 集成 pip 入门
date: 2026-09-07 12:10:00
tags:
  - Dragonfly
  - pip
  - 入门
categories:
  - Dragonfly 新手入门
---

大规模节点 `pip install` 同一依赖时，PyPI/内网源易成瓶颈。Dragonfly 可加速 Python 包分发。

## 要点

- 配置索引/代理走 Peer
- 锁定版本（requirements.hash）提高缓存命中
- CI 与在线集群策略一致

> 官方文档：[pip](https://d7y.io/docs/next/operations/integrations/pip/)

