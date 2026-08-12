---
title: NVIDIA 驱动升级与 GPU 节点滚动迁移
date: 2026-08-25 12:15:00
tags:
  - nvidia-smi
  - SRE
  - 升级
categories:
  - nvidia-smi SRE
---

驱动升级是 GPU 池最高风险变更之一，必须**滚动、可回滚、可验证**。

## 变更前

- [ ] 新版本在 staging 跑通典型 workload（训练 + 推理）
- [ ] 阅读 Release Notes（XID 修复、MIG、CUDA 兼容）
- [ ] 备份当前驱动版本号：`nvidia-smi --query-gpu=driver_version --format=csv`
- [ ] 通知平台：预留维护窗口

## 滚动流程（K8s 节点）

```
1. kubectl cordon <node>
2. kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
3. 安装新驱动（Ansible/脚本）
4. reboot（若需要）
5. nvidia-smi 全量验收
6. 测试 Pod：nvidia-smi + 短跑 benchmark
7. kubectl uncordon
8. 观察 24h → 下一节点
```

## 验收命令

```bash
nvidia-smi -L
nvidia-smi --query-gpu=driver_version,name,ecc.mode.current --format=csv
nvidia-smi -q -d PERFORMANCE,CLOCK,POWER | head -80
```

对比变更前后 query 输出，存档 Git/工单。

## 回滚

- 保留上一版驱动包或 Golden AMI
- 回滚后同样执行 smi 验收
- 若 MIG：确认 profile 脚本重新应用

## 与作业迁移

| 环境 | 策略 |
|------|------|
| Slurm | 节点 drain 后作业自动重调度 |
| K8s | drain + PDB 协调 |
| 裸金属长训 | 等 checkpoint 完成再 cordon |

## 反模式

- 全池同时升级
- 升级后不跑 workload 冒烟
- 无 driver_version 指标，无法发现漂移

驱动版本应写入 Prometheus：`nvidia_smi_driver_version` textfile 或 DCGM 自定义字段。
