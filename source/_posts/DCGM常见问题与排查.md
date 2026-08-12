---
title: DCGM 常见问题与排查
date: 2026-08-23 13:00:00
tags:
  - DCGM
  - 排查
categories:
  - DCGM 新手入门
---

DCGM 部署与使用中常见问题汇总。

## Host Engine 无法启动

```bash
systemctl status nvidia-dcgm
journalctl -u nvidia-dcgm -n 50
```

| 原因 | 解决 |
|------|------|
| 驱动未装 | 装 NVIDIA driver |
| 驱动版本低 | 升级驱动/DCGM |
| 端口占用 | 检查 socket 冲突 |

## dcgmi 连接失败

```
Error: Unable to connect to host engine
```

```bash
systemctl start nvidia-dcgm
# 或
nv-hostengine &
export DCGM_HOSTENGINE_ADDR=127.0.0.1:5555
```

## dcgm-exporter 无 metrics

| 原因 | 解决 |
|------|------|
| 无 GPU | 节点无卡或非 NVIDIA runtime |
| 权限 | 加 SYS_ADMIN |
| MIG 配置 | 检查 MIG 模式 |
| 镜像版本 | 对齐驱动版本 |

```bash
curl localhost:9400/metrics
kubectl logs -n gpu-operator ds/dcgm-exporter
```

## 指标全 0 或 N/A

- GPU 空闲时 Util=0 正常
- Field 不支持该 GPU 型号
- csv 配置文件缺 field

## XID 错误

```bash
nvidia-smi -q -x | grep -i xid
dcgmi health -g 1 -c
```

| XID | 常见含义 |
|-----|----------|
| 13 | 图形/驱动异常 |
| 31 | GPU 内存页故障 |
| 43 | GPU 停止响应 |
| 48 | 双位 ECC 错误 |

处理：记录 → 隔离节点 → 换卡/RMA。

## Prometheus 无数据

- target down：网络/防火墙 9400
- 标签不匹配：Dashboard 变量 filter 错误
- scrape interval 过长

## 排查流程

```
1. nvidia-smi 正常？
2. hostengine 运行？
3. dcgmi discovery -l 有 GPU？
4. curl exporter /metrics 有 DCGM_ 前缀？
5. Prometheus target UP？
6. Grafana PromQL 有数据？
```

逐层缩小范围，**不要跳过 nvidia-smi**。
