---
title: MIG 生产切分与运维 SRE 实践
date: 2026-08-25 11:00:00
tags:
  - nvidia-smi
  - SRE
  - MIG
categories:
  - nvidia-smi SRE
---

MIG（Multi-Instance GPU）将 A100/H100 等切分为独立实例，SRE 需管理**切分模板、变更窗口、监控粒度**。

## 状态查看

```bash
nvidia-smi -L
nvidia-smi -i 0 -q | grep -A20 "MIG Mode"
nvidia-smi mig -lgi
nvidia-smi mig -lci
```

## 生产切分流程（摘要）

1. **维护窗口** cordon 节点，确认无运行作业
2. 启用 MIG：`sudo nvidia-smi -i 0 -mig 1`
3. 创建 GPU Instance / Compute Instance（按 NVIDIA 文档固定 profile）
4. `nvidia-smi -L` 验证实例列表
5. 更新 K8s 标签 / Device Plugin 配置
6. 跑冒烟推理/训练验证

## 常见 Profile（A100 40GB 示例）

| Profile | 显存/实例 | 适用 |
|---------|-----------|------|
| 1g.5gb | 7 实例 | 小推理 |
| 3g.20gb | 2 实例 | 中等模型 |
| 7g.40gb | 1 实例 | 近整卡 |

具体以硬件文档为准，**生产固定 1~2 种模板**，避免随意组合。

## 监控注意

- MIG 实例在 smi 中显示为 `MIG 1g.5gb Device 0` 等
- DCGM 需支持 MIG 字段，告警按 **GI/CI** 粒度
- 实例级显存：`nvidia-smi --query-gpu=index,mig.mode.current,memory.used --format=csv`

## 变更风险

| 操作 | 影响 |
|------|------|
| 修改 MIG profile | 需销毁实例，中断所有作业 |
| 驱动升级 | 可能重置 MIG，需 IaC 自动重建 |
| 节点 reboot | 验证 MIG 配置是否持久化 |

## 反模式

- 手工切分无文档，重启后实例丢失
- 训练大作业调度到 MIG 小实例
- 未在 Prometheus 区分物理 GPU 与 MIG UUID

MIG 配置应 **Infrastructure as Code**（脚本 + Git），变更前后各存 `nvidia-smi mig -lgi` 输出。
