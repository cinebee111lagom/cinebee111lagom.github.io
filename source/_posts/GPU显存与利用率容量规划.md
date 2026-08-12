---
title: GPU 显存与利用率容量规划
date: 2026-08-25 10:15:00
tags:
  - nvidia-smi
  - SRE
  - 容量
categories:
  - nvidia-smi SRE
---

GPU 容量不仅是「卡数」，更是**显存、算力、PCIe 带宽**的综合水位。

## 容量维度

| 指标 | 采集 | 规划参考 |
|------|------|----------|
| 显存使用率 | smi / DCGM | 池均值 < 75%，峰值 < 90% |
| GPU 利用率 | smi / DCGM | 训练 70%+，推理视 SLA |
| 卡数分配率 | K8s 调度 | 可调度 GPU / 物理 GPU |
| 功耗 | smi power.draw | 机柜 PDU 上限 |

## 现场容量查看

```bash
# 各卡显存占用
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu \
  --format=csv

# 进程级显存
nvidia-smi --query-compute-apps=gpu_uuid,pid,used_gpu_memory,process_name \
  --format=csv
```

## 容量模型（简化）

```
所需卡数 = ceil(峰值并发作业显存需求 / 单卡可用显存 × 安全系数)
安全系数：1.15 ~ 1.25（预留碎片与系统占用）
```

## 扩容信号

- 连续 7 天池显存 P95 > 85%
- 排队作业 > N 且 GPU 利用率长期高位
- 频繁 OOM（CUDA out of memory）工单

## 缩容信号

- 池利用率 P50 < 30% 持续 30 天
- MIG/共享可进一步提高密度

## SRE 动作

1. 周报：`nvidia-smi` 或 Prometheus 导出池级显存/利用率
2. 大促/大模型上线前压测留 **baseline 快照**
3. CMDB 记录：**型号、显存、驱动、上架日期**

## 反模式

- 只数卡数不看显存碎片
- 不区分训练（占满显存）与推理（低 util 高显存）
- 无 process 级归因，无法找「显存大户」

容量评审应附带 **Top N 进程显存** 与 **按队列/租户分摊** 数据。
