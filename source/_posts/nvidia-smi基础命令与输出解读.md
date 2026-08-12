---
title: nvidia-smi 基础命令与输出解读
date: 2026-08-24 09:30:00
tags:
  - nvidia-smi
  - 基础
categories:
  - nvidia-smi 新手入门
---

默认 `nvidia-smi` 输出一张表，新手需逐项读懂。

## 默认输出结构

```
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |         Memory-Usage | GPU-Util  Compute M. |
|                               |                      |               MIG M. |
|===============================+======================+======================|
|   0  NVIDIA A100-SXM...  On  | 00000000:00:04.0 Off |                    0 |
| N/A   42C    P0             68W / 400W |  15234MiB / 40960MiB |     95%      Default |
```

## 字段解读

| 字段 | 含义 |
|------|------|
| GPU | 编号，从 0 开始 |
| Name | 型号 |
| Persistence-M | 持久化模式 On/Off |
| Bus-Id | PCIe 地址 |
| Disp.A | 是否连接显示器 |
| Temp | 温度 °C |
| Perf | 性能状态 P0~P12（P0 最高） |
| Pwr:Usage/Cap | 当前功耗 / 功耗上限 |
| Memory-Usage | 已用显存 / 总显存 |
| GPU-Util | GPU 计算利用率 % |
| Compute M. | 计算模式 Default/Exclusive 等 |
| MIG M. | MIG 模式是否启用 |

## 底部进程段

```
|  GPU   GI   CI        PID   Type   Process name                            GPU Memory |
|        ID   ID                                                               Usage      |
|    0   N/A  N/A    123456      C   python train.py                          15000MiB |
```

| 字段 | 含义 |
|------|------|
| PID | 进程 ID |
| Type | C=Compute, G=Graphics |
| GPU Memory Usage | 该进程占用显存 |

## 常用简短命令

```bash
nvidia-smi -L              # 只列 GPU 名称
nvidia-smi -i 0            # 只看 GPU 0
nvidia-smi -h              # 帮助
man nvidia-smi
```

## 刷新监控

```bash
nvidia-smi -l 2            # 每 2 秒刷新（Ctrl+C 退出）
nvidia-smi dmon            # 动态监控模式（下篇详述）
```

## 状态速判

| 现象 | 可能含义 |
|------|----------|
| GPU-Util 0%，有进程 | 等数据/I/O |
| GPU-Util 100% | 计算饱和 |
| Perf 非 P0 | 空闲降频或 thermal throttle |
| Memory 满 | OOM 风险 |

读懂默认输出，80% 日常问题已能初步定位。
