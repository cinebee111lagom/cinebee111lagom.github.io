---
title: DCGM 新手学习路径与入门 Checklist
date: 2026-08-23 13:45:00
tags:
  - DCGM
  - 入门
  - 学习路径
categories:
  - DCGM 新手入门
---

## 推荐学习路径

```
第 1 周：概念 + 安装 + dcgmi 基础
  └─ 篇 1~4

第 2 周：指标解读 + smi 对比 + 健康检查
  └─ 篇 5~7

第 3 周：Prometheus + exporter + Grafana
  └─ 篇 8~10、16

第 4 周：多卡/MIG/K8s/进程监控
  └─ 篇 11~15

第 5 周：实战 + 排查 + API
  └─ 篇 17~20
```

## 入门 Checklist

### 基础

- [ ] nvidia-smi 正常，驱动版本满足 DCGM 要求
- [ ] Host Engine 启动，`dcgmi discovery -l` 可见 GPU
- [ ] 会用 `dcgmi dmon` 看温度/功耗/利用率
- [ ] 理解 Field、Group、Host Engine 关系

### 监控

- [ ] dcgm-exporter 部署，`/metrics` 有 DCGM_ 指标
- [ ] Prometheus scrape 成功
- [ ] Grafana Dashboard 有数据
- [ ] 配置至少 2 条告警（温度、XID）

### 进阶

- [ ] 会读 Health Check 输出
- [ ] 理解 NVLink/PCIe 拓扑
- [ ] K8s GPU Operator + dcgm-exporter 部署
- [ ] 完成 GPU 集群监控实战

### 延伸（后续可学）

- GPU SRE 系列（故障演练、容量规划）
- NCCL 网络调优
- MIG 多租户平台

## 配套练习

| 练习 | 技能点 |
|------|--------|
| 单机 dmon 5 分钟 | 指标实时观察 |
| 导出 Prometheus 指标 | exporter 部署 |
| 模拟 XID 查文档 | 健康排查 |
| Import Grafana 12239 | 可视化 |
| 写巡检 shell 脚本 | health + smi |

## 推荐资源

- [NVIDIA DCGM 官方文档](https://docs.nvidia.com/datacenter/dcgm/latest/)
- [dcgm-exporter GitHub](https://github.com/NVIDIA/dcgm-exporter)
- [GPU Operator 文档](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/)

---

**DCGM 新手入门系列 20 篇**完结，从零到能独立搭建 GPU 集群 Prometheus 监控。建议配合 **GPU 调度** 系列、**Kubernetes SRE** 对照阅读。
