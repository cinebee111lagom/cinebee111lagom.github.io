---
title: DCGM 进程级 GPU 监控
date: 2026-08-23 12:00:00
tags:
  - DCGM
  - 进程
categories:
  - DCGM 新手入门
---

定位「哪张卡、哪个进程」占用 GPU，是运维排障高频需求。

## nvidia-smi 进程视图

```bash
nvidia-smi pmon -c 1
nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory,gpu_uuid --format=csv
```

## dcgmi stats

```bash
# 查看 GPU 0 上所有活跃 job 统计
dcgmi stats -g 1 -e

# 指定 PID
dcgmi stats --gpuid 0 --pid 123456

# 按进程名
dcgmi stats --gpuid 0 --process python
```

输出包括：SM 利用率、显存、PCIe/NVLink 流量等（视版本）。

## K8s 环境

Pod 内 PID 与宿主机不同，需结合：

```bash
# 宿主机
nvidia-smi --query-compute-apps=pid,used_gpu_memory --format=csv

# 对应 container
crictl ps | grep training
# /proc/<pid>/cgroup 找 container id
```

NVIDIA GPU Operator 可选 **gpu-feature-discovery** 标注节点。

## Prometheus 进程指标

dcgm-exporter 默认偏设备级；进程级可用：

- `nvidia_smi_exporter`（第三方）
- DCGM `DCGM_FI_PROF_*` 部分版本
- 结合 cAdvisor + GPU 显存 by pod（K8s）

K8s 推荐：**DCGM 设备指标 + kube-state-metrics 按 Pod 关联**。

## 计费与配额

```bash
# 记录训练 job 起止
dcgmi stats --gpuid 0 --pid $PID --start
# ... 训练结束
dcgmi stats --gpuid 0 --pid $PID --stop
```

平台可据此统计 GPU·小时。

## 排查「显存被占满」

```bash
nvidia-smi
# 看 Processes 段 PID

kill -9 <pid>   # 谨慎，确认可杀

# 僵尸进程 / 驱动未释放
nvidia-smi --gpu-reset -i 0   # 需无进程，影响大
```

进程级监控连接**用户投诉**与**具体进程**。
