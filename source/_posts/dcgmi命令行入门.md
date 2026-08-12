---
title: dcgmi 命令行入门
date: 2026-08-23 09:45:00
tags:
  - DCGM
  - dcgmi
categories:
  - DCGM 新手入门
---

`dcgmi` 是 DCGM 官方 CLI，日常巡检、调试都从这里开始。

## 发现 GPU

```bash
# 列出所有 GPU
dcgmi discovery -l

# 详细拓扑（NVLink、CPU 亲和）
dcgmi discovery -c
dcgmi topo
```

## 实时监控

```bash
# 监控 GPU 0 的温度、功耗、利用率（每 1 秒刷新）
dcgmi dmon -e 155,156,203,252 -d 1

# 常用 field ID（示例，版本间可查文档）
# 155: SM 时钟  156: 内存时钟  203: 功耗  252: GPU 利用率
```

```bash
# 查看支持的 field
dcgmi dmon --list
```

## 查询快照

```bash
# 单次查询所有 GPU 利用率
dcgmi stats -g 1 -e

# 进程统计
dcgmi stats --gpuid 0 --pid $(pgrep -f python | head -1)
```

## 健康检查

```bash
# 启动健康监控
dcgmi health -g 1 -s a

# 查看健康状态
dcgmi health -g 1 -c
```

## Group 管理

```bash
dcgmi group -c mygroup -a 0,1
dcgmi group -l
dcgmi group -d mygroup
```

## 配置

```bash
# 查看 GPU 配置
dcgmi config --help

# 设置应用时钟（需管理员）
dcgmi config -g 1 -e 2100,900
```

## 常用组合

```bash
# 快速巡检脚本
dcgmi discovery -l
dcgmi health -g 1 -c
dcgmi dmon -e 203,252,150,151 -d 5 -c 3
# 功耗、利用率、显存 used/free，5 秒间隔，3 次
```

## 帮助

```bash
dcgmi --help
dcgmi dmon --help
man dcgmi
```

`dcgmi` 是**单机调试利器**，生产长期监控交给 dcgm-exporter + Prometheus。
