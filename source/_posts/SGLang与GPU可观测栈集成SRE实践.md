---
title: SGLang 与 GPU 可观测栈集成 SRE 实践
date: 2026-09-06 13:15:00
tags:
  - SGLang
  - SRE
  - GPU
categories:
  - SGLang SRE
---

应用指标 + GPU 指标一起看，才能区分 **软件排队** 与 **硬件瓶颈**。

## 栈建议

```
SGLang /metrics
DCGM / nvidia-smi exporter
节点 CPU/内存/磁盘
      ↓
Prometheus → Grafana
      ↓
告警 + 值班
```

## 关联分析

| 组合 | 解读 |
|------|------|
| 高排队 + GPU util 低 | 可能调度/锁/加载问题，或请求未到 GPU |
| 高排队 + GPU util 高 | 算力不足 |
| 显存高 + OOM 重启 | 并发/上下文过大 |
| TTFT 差 + 命中率跌 | 缓存被打散或冷启动 |
| 功耗/温度异常 | 硬件或降频 |

## 落地要点

- 标签对齐：`node`、`pod`、`model`、`gpu_uuid`  
- 同一时间轴对比应用与 DCGM 面板  
- 采样间隔足够（过粗会漏尖峰）  

## 反模式

- 只看 nvidia-smi 截图排障  
- GPU 与应用监控分属两套、无法关联  
- 忽略 NVLink/PCIe 拓扑对 TP 的影响  

**排障最小集：请求指标 + 显存/util + 最近变更。**
