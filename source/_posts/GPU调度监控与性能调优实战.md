---
title: GPU 调度监控与性能调优实战!!!
date: 2026-08-12 21:12:39
tags:
  - GPU调度
  - 监控
  - 调优
categories:
  - GPU调度
---

没有可观测性，调度策略就是盲人摸象。生产环境需要 **指标、追踪、告警** 闭环，持续验证调度是否有效。

## 核心监控指标

### 利用率维度

- `DCGM_FI_DEV_GPU_UTIL`：SM 利用率
- `DCGM_FI_PROF_GR_ENGINE_ACTIVE`：图形/计算引擎活跃比
- NVENC/NVDEC 利用率（视频必备）

### 显存维度

- `DCGM_FI_DEV_FB_USED / FREE`
- 按进程 / Pod 的显存归因（`nvidia-smi pmon`）

### 调度健康度

- Pod **Pending 时长**
- 队列 **积压长度**
- GPU **分配率 vs 实际利用率**（识别「占卡不用」）

## 工具栈推荐

| 工具 | 用途 |
|------|------|
| DCGM Exporter + Prometheus | 集群指标 |
| Grafana Dashboard | 可视化 |
| Nsight Systems | 单任务时间线 |
| Nsight Compute | Kernel 级分析 |
| eBPF / GPU telemetry | 低开销持续采样 |

## 常见调优路径

### 现象：利用率低、延迟高

- 检查是否默认 Stream 导致串行
- 检查 PCIe 是否瓶颈（小 kernel 频繁传数据）
- 视频场景：是否没用 NVENC 而走软编

### 现象：多任务 OOM

- 启用 MIG 或限制并发 Slot
- 训练侧：Gradient Checkpointing / ZeRO

### 现象：P99 延迟抖动

- 避免 MPS 混部延迟敏感任务
- 隔离 NVENC 路与训练任务到不同卡

## 告警规则示例

```yaml
# Prometheus 示例
- alert: GpuMemoryNearFull
  expr: DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL > 0.9
  for: 5m

- alert: GpuUtilizationLowWhileQueueHigh
  expr: queue_depth > 100 and avg_gpu_util < 0.3
  for: 10m
```

第二条直指 **调度失效**：队列堆积但卡闲着，说明分配策略或 Slot 配置有问题。

## 闭环优化流程

1. 压测得出单卡 **安全并发路数 / 显存曲线**
2. 写入调度器配置（MIG profile、Queue quota）
3. 上线监控与告警
4. 每周复盘：利用率、SLA、成本三角

GPU 调度不是一次配置永久有效——新模型、新 codec、新硬件都会改变最优策略。持续监控才是调优的起点。

---

以上十篇覆盖了从 CUDA Stream 到集群调度、从视频转码到训练显存的 GPU 调度全景。建议按入门 → 单卡 → 集群 → 场景 → 运维的顺序阅读。
