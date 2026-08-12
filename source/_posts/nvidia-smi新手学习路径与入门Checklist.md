---
title: nvidia-smi 新手学习路径与入门 Checklist
date: 2026-08-24 13:45:00
tags:
  - nvidia-smi
  - 入门
  - 学习路径
categories:
  - nvidia-smi 新手入门
---

## 推荐学习路径

```
第 1 周：驱动 + 默认输出 + 查询
  └─ 篇 1~4

第 2 周：监控 + 进程 + 拓扑
  └─ 篇 5~7

第 3 周：功耗/ECC/MIG + dmon/pmon
  └─ 篇 8~11

第 4 周：格式化输出 + CUDA + 多卡
  └─ 篇 12~14

第 5 周：Docker/K8s + 排查 + 实战
  └─ 篇 15~19
```

## 入门 Checklist

### 基础

- [ ] `nvidia-smi` 正常输出
- [ ] 读懂默认表各字段含义
- [ ] 会用 `-L`、`-i`、`--query-gpu` CSV 输出
- [ ] 会查进程和显存占用

### 进阶

- [ ] 会用 `dmon`/`pmon` 持续监控
- [ ] 会读 `topo -m` 拓扑矩阵
- [ ] 理解 CUDA Version 与驱动关系
- [ ] 会用 `CUDA_VISIBLE_DEVICES` 指定 GPU
- [ ] 了解 MIG 基本概念

### 运维

- [ ] Docker `--gpus all` 验证
- [ ] K8s GPU Pod 内 smi 验证
- [ ] 会查 ECC 和 dmesg XID
- [ ] 完成 gpu-check 巡检脚本
- [ ] 知道何时升级到 DCGM 监控

## 配套练习

| 练习 | 技能点 |
|------|--------|
| 解释一次默认 smi 输出 | 字段理解 |
| CSV 导出温度/利用率 | 脚本化 |
| 找出占显存最大的 PID | 进程排查 |
| 画 topo 矩阵 | 多卡互联 |
| 容器内跑 smi | Docker GPU |

## 延伸系列

| 系列 | 关系 |
|------|------|
| DCGM 新手入门 | 生产监控升级 |
| GPU 调度 | 业务调度层 |
| GPU 切分 | MIG/vGPU 深入 |

## 推荐资源

- `man nvidia-smi`
- `nvidia-smi --help-query-gpu`
- [NVIDIA NVML 文档](https://docs.nvidia.com/deploy/nvml-api/index.html)

---

**nvidia-smi 新手入门系列 20 篇**完结，从零到能独立巡检 GPU 节点、排查常见问题。建议下一步学习 **DCGM 新手入门** 系列，构建完整 GPU 可观测性。
