---
title: Dragonfly 二进制安装入门
date: 2026-09-07 10:10:00
tags:
  - Dragonfly
  - 安装
  - 入门
categories:
  - Dragonfly 新手入门
---

非 K8s 或调试场景可用 **二进制** 安装 Scheduler / Manager / dfdaemon 等组件。

## 适用

- 裸机 / VM POC
- 排障时单组件拉起
- 与 systemd 集成的固定机房

## 要点

- 版本对齐（各组件同一发行线）
- 配置文件路径、证书、数据目录提前规划
- 生产仍优先 Helm + K8s，二进制适合边缘特例

> 官方文档：[Binaries](https://d7y.io/docs/next/getting-started/installation/binaries/)

