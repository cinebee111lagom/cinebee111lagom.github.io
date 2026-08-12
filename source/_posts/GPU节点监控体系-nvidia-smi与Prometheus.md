---
title: GPU 节点监控体系：nvidia-smi 与 Prometheus
date: 2026-08-25 10:00:00
tags:
  - nvidia-smi
  - SRE
  - Prometheus
categories:
  - nvidia-smi SRE
---

生产监控分层：**DCGM/exporter 做主监控**，**nvidia-smi 做兜底与现场**。

## 监控架构

```
GPU 节点
  ├─ dcgm-exporter:9400 → Prometheus → Grafana
  ├─ node_exporter → 主机 CPU/内存/磁盘
  └─ cron: nvidia-smi 巡检脚本 → 日志/告警 webhook
```

## smi 可脚本化指标

```bash
# 利用率、显存、温度、功耗（CSV 便于解析）
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw \
  --format=csv,noheader,nounits

# ECC
nvidia-smi --query-gpu=index,ecc.errors.uncorrected.aggregate.total \
  --format=csv,noheader
```

## 轻量 textfile collector 示例

```bash
#!/bin/bash
OUT=/var/lib/node_exporter/textfile_collector/gpu_smi.prom
{
  nvidia-smi --query-gpu=index,utilization.gpu,memory.used,temperature.gpu \
    --format=csv,noheader,nounits | while IFS=, read idx util mem temp; do
    echo "gpu_utilization{gpu=\"$idx\"} $util"
    echo "gpu_memory_used_mib{gpu=\"$idx\"} $mem"
    echo "gpu_temperature_celsius{gpu=\"$idx\"} $temp"
  done
} > "$OUT.$$" && mv "$OUT.$$" "$OUT"
```

配合 cron 每分钟执行，适合尚未部署 DCGM 的环境。

## 核心 Dashboard 面板

| 面板 | 来源 |
|------|------|
| GPU 利用率 | DCGM / smi |
| 显存使用率 | DCGM / smi |
| 温度 / 功耗 | DCGM / smi |
| XID / ECC | DCGM + dmesg |
| GPU 掉线 | up{job="dcgm"} 或 smi 脚本 exit code |

## 与 DCGM 分工

| 场景 | 工具 |
|------|------|
| 长期趋势、告警 | DCGM |
| 值班第一反应 | nvidia-smi |
| 变更验收 | nvidia-smi 快照对比 |

## 反模式

- 仅依赖人工 ssh + smi，无历史曲线
- smi cron 与 DCGM 指标命名不一致，Dashboard 重复
- 未监控 exporter 自身存活

监控上线标准：**任一 GPU 不可见 5 分钟内触发 P0**。
