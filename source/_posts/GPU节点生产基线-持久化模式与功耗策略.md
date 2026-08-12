---
title: GPU 节点生产基线：持久化模式与功耗策略
date: 2026-08-25 09:45:00
tags:
  - nvidia-smi
  - SRE
  - 基线
categories:
  - nvidia-smi SRE
---

GPU 节点上线后应应用统一基线，避免「同池不同配置」导致性能与稳定性差异。

## 推荐基线项

| 项 | 训练节点 | 推理节点 |
|----|----------|----------|
| 持久化模式 `-pm 1` | 推荐 | 可选 |
| ECC | 开启（数据中心卡） | 开启 |
| 功耗上限 | 默认或 TDP | 可按卡型限制 |
| 计算模式 | Default | Default |
| MIG | 按需 | 常用 |

## 持久化模式

```bash
# 查看
nvidia-smi -q -d PERFORMANCE | grep "Persistence Mode"

# 开启（重启后需 systemd 或 rc.local 持久化）
sudo nvidia-smi -pm 1
```

减少 CUDA 上下文初始化延迟，训练池强烈建议开启。

## 功耗管理

```bash
# 查看功耗上限
nvidia-smi -q -d POWER | grep -A2 "Power Limit"

# 设置（示例：300W，需管理员权限）
sudo nvidia-smi -pl 300
```

推理混部时可降功耗上限，避免单卡抢电导致整机不稳定。

## 基线脚本示例

```bash
#!/bin/bash
# gpu-baseline.sh
for i in $(nvidia-smi --query-gpu=index --format=csv,noheader); do
  sudo nvidia-smi -i $i -pm 1
done
nvidia-smi --query-gpu=index,persistence_mode,power.limit,ecc.mode.current \
  --format=csv
```

## 验收 Checklist

- [ ] 所有 GPU Persistence Mode: Enabled
- [ ] ECC Mode 符合策略
- [ ] 无异常降频（`nvidia-smi -q -d CLOCK`）
- [ ] 基线输出已归档 CMDB

## 反模式

- 仅部分节点开持久化模式
- 手动 `-pl` 后未写入 IaC，重启丢失
- 不监控 `clocks_event_reasons` 导致 silent throttle

基线变更视为**生产变更**，需变更单与回滚方案。
