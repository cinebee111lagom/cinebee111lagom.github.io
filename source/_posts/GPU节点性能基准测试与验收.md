---
title: GPU 节点性能基准测试与验收
date: 2026-08-25 13:00:00
tags:
  - nvidia-smi
  - SRE
  - 压测
categories:
  - nvidia-smi SRE
---

新 GPU 节点上架、驱动升级、RMA 换卡后，需 **基准测试 + nvidia-smi 快照** 验收。

## 验收流程

```
1. nvidia-smi 硬件信息快照
2. 单机 GPU 算力/带宽压测
3. 多卡 NCCL（若训练节点）
4. 典型业务冒烟
5. 结果入库 CMDB
```

## smi 快照（必存）

```bash
nvidia-smi -L > /opt/gpu-baseline/$(hostname)-gpu-list.txt
nvidia-smi -q > /opt/gpu-baseline/$(hostname)-smi-q.txt
nvidia-smi topo -m > /opt/gpu-baseline/$(hostname)-topo.txt
nvidia-smi --query-gpu=index,name,driver_version,memory.total,pcie.link.gen.max \
  --format=csv > /opt/gpu-baseline/$(hostname)-summary.csv
```

## 压测工具

| 工具 | 测什么 |
|------|--------|
| gpu-burn | 稳定性、散热 |
| nccl-tests | 多卡 AllReduce |
| ib_write_bw | 网络（多机） |
| 业务短训 | 端到端 step time |

## 压测期间监控

```bash
# 另开终端
nvidia-smi dmon -s pucvmet -d 5
watch -n 5 nvidia-smi --query-gpu=temperature.gpu,power.draw,clocks.sm \
  --format=csv
```

关注：温度 < 阈值、无 throttle、无 XID。

## 通过标准（示例，按机型调整）

| 指标 | A100 8 卡训练节点 |
|------|-------------------|
| nccl AllReduce | ≥ 基线 95% |
| 单卡 FP16 TFLOPS | ≥ 规格 90% |
| 压测 1h | 0 XID，0 uncorrected ECC |
| 峰值温度 | < 85°C |

## 反模式

- 只看 smi 不跑压测
- 无 baseline 对比，升级后性能退化未发现
- 压测未监控 ECC/XID

基准数据是 **性能回归** 与 **RMA 争议** 的关键证据。
