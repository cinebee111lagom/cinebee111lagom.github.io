---
title: vLLM 与 GPU 可观测栈集成 SRE 实践
date: 2026-09-04 13:45:00
tags:
  - vLLM
  - SRE
  - GPU
categories:
  - vLLM SRE
---

vLLM 指标要与 **nvidia-smi / DCGM** 打通，才能区分「引擎问题」还是「硬件问题」。

## 集成架构

```
vLLM /metrics          → Prometheus
dcgm-exporter          → Prometheus
node_exporter          → Prometheus
API 网关指标           → Prometheus
                ↓
         Grafana 统一大盘
                ↓
         告警 → Oncall
```

## 联合排查

| 现象 | vLLM | GPU 栈 |
|------|------|--------|
| TTFT 高 | 队列、prefill | util 低？可能 CPU/IO |
| 间歇失败 | 5xx 日志 | XID、ECC、掉卡 |
| 吞吐掉 | 参数变更 | 降频、温度、功耗墙 |
| OOM | max_seqs/len | 显存占用、碎片 |

## 值班建议面板

1. 业务：QPS、TTFT、429/5xx  
2. 引擎：waiting/running、token/s  
3. 硬件：GPU util、显存、温度、XID  
4. 节点：磁盘延迟（模型加载）  

## 与系列对照

- **nvidia-smi / DCGM 新手与 SRE**：硬件与指标  
- **vLLM 新手入门**：引擎操作  
- **本篇**：二者在生产值班中的接合  

## 反模式

- 两套监控互不链接，工单踢皮球
- 只认应用日志，忽略 XID
- GPU 告警无模型池标签

---

**vLLM SRE 系列 20 篇**完结。建议与 **vLLM 新手入门**、**nvidia-smi SRE**、**DCGM** 系列对照阅读。
