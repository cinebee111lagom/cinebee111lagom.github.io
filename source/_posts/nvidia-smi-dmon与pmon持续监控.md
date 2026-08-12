---
title: nvidia-smi dmon 与 pmon 持续监控
date: 2026-08-24 11:30:00
tags:
  - nvidia-smi
  - dmon
  - pmon
categories:
  - nvidia-smi 新手入门
---

`dmon` 和 `pmon` 是 nvidia-smi 内置的持续监控模式，比 `-l` 刷新更专业。

## dmon（Device Monitor）

监控 GPU 设备级指标：

```bash
nvidia-smi dmon -h              # 帮助

# 常用：功耗、利用率、显存、温度
nvidia-smi dmon -s pucvmet -d 1

# 指定 GPU
nvidia-smi dmon -i 0,1 -s u -d 2 -c 20
# -d 间隔秒  -c 采样次数（省略则无限）
```

### -s 参数组合

| 字符 | 监控项 |
|------|--------|
| p | power |
| u | sm/util |
| c | compute |
| v | framebuffer |
| m | mem controller |
| e | ecc |
| t | temperature |
| n | fan |

## pmon（Process Monitor）

监控进程级 GPU 使用：

```bash
nvidia-smi pmon -d 1 -c 10
nvidia-smi pmon -s um -d 1    # u=SM%, m=mem%
```

输出示例：

```
# gpu        pid  type    sm   mem   enc   dec   command
#   0     123456     C    95    80     -     -   python
```

## 对比

| | dmon | pmon | -l 刷新 |
|---|------|------|---------|
| 粒度 | 设备 | 进程 | 全表 |
| 开销 | 低 | 低 | 较高 |
| 脚本 | ✅ | ✅ | 一般 |

## 写入日志

```bash
nvidia-smi dmon -s pucv -d 5 -o DT >> /var/log/gpu-dmon.log
# -o DT：输出含日期时间
```

## 与 watch 对比

```bash
watch -n 1 nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv
```

dmon 格式更紧凑，适合**终端实时盯盘**。

## 局限

- 无历史存储 → 需自行写文件或改用 DCGM
- 无告警 → 配合脚本 threshold 判断

```bash
util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits -i 0)
[ "$util" -gt 95 ] && echo "GPU0 busy"
```

dmon/pmon 是单机调试的利器，集群监控交给 Prometheus。
