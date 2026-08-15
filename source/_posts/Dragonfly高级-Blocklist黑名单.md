---
title: Dragonfly 高级：Blocklist 黑名单
date: 2026-09-08 10:30:00
tags:
  - Dragonfly
  - Blocklist
  - 进阶
categories:
  - Dragonfly 进阶指南
---

Blocklist 用于拦截不应走 P2P/代理的地址或资源，避免错误加速或安全风险。

## 用途

- 排除内网敏感地址误配
- 屏蔽不适合缓存的动态 URL
- 与安全策略联动

配置后验证：命中黑名单的请求行为符合预期（拒绝或直连策略按文档）。

> 官方文档：[Blocklist](https://d7y.io/docs/next/advanced-guides/blocklist/)

