---
title: GPU 硬件与故障排查深入补充
date: 2026-09-08 08:30:00
tags:
  - GPU
  - HBM
  - 故障排查
  - 硬件
categories:
  - GPU
---

## 一、显存结构的进一步拆解

### HBM 物理结构

HBM 并非单颗芯片，而是通过 **TSV（硅穿孔）** 堆叠多层 DRAM die + 一片逻辑 die 的 3D 封装结构：

| 参数 | A100 80GB | H100 80GB | H200 |
|---|---|---|---|
| HBM 版本 | HBM2e | HBM3 | HBM3e |
| 堆叠数 | 5 stacks × 2-Hi | 6 stacks × 6-Hi | 6 stacks |
| 单 stack 容量 | 16 GB | ~13.3 GB | ~16.6 GB |
| 总带宽 | 2.0 TB/s | 3.35 TB/s | 4.8 TB/s |

**关键理解**：某一个 stack 出故障 ≠ 整张卡报废。ECC 可以在一定范围内容忍，但 **Double Bit Error（不可纠正）** 一旦出现在同一行多次，就需要隔离该 GPU。

### ECC 工作机制

```
┌─────────────────────────────────────────────┐
│              DRAM Cell Array                 │
│                                              │
│  数据位 (64-bit data)    ECC 校验位 (8-bit)  │
│         ↓                      ↓             │
│   ┌───────────┐        ┌──────────┐          │
│   │ 原始数据  │───────→│ SECDED 编码 │        │
│   └───────────┘        └──────────┘          │
│                              ↓               │
│              Single-bit → 自动纠正（静默）     │
│              Double-bit → 上报 Xid，无法纠正   │
└─────────────────────────────────────────────┘
```

**SECDED（Single Error Correction, Double Error Detection）**：消费级 GPU 往往不带 ECC，A100/H100 等计算卡标配。

查看 ECC 状态：

```bash
nvidia-smi -q | grep -A 4 "ECC Mode"
# 或逐 GPU 查看
nvidia-smi -i 0 -q | grep -A 10 "ECC"
```

---

## 二、Xid 错误码 — 实战速查

| Xid | 含义 | 严重程度 | 处理方式 |
|---|---|---|---|
| **13** | GR: Graphics Engine Exception | 中 | 通常是 CUDA 程序 bug，检查 kernel 代码 |
| **31** | GPU Memory Page Fault | 中 | 越界访问显存，检查模型是否 OOM |
| **43** | GPU stopped processing | 高 | 一般伴随 ECC 错误，需排查硬件 |
| **48** | Double Bit ECC Error | **极高** | 不可纠正，需要隔离 GPU，报修 |
| **63** | ECC Page Retirement (行退役) | 中高 | 行退役后继续可用，但退役行数增长需警惕 |
| **74** | NVLink LTSSM Timeout | 高 | 检查 NVLink 线缆和交换机 |
| **79** | GPU fallen off the bus | **极高** | 硬件级故障，GPU 可能已物理损坏 |
| **94** | Contained ECC Error | 中 | 已纠正，需监控是否频繁出现 |
| **95** | Uncontained ECC Error | 高 | 无法确保数据正确性，需停用 |

**查询 Xid 日志**：

```bash
# 实时监控
dmesg | grep -i "NVRM\|Xid"

# 结构化查询（推荐）
journalctl -k | grep -i "Xid"

# 统计频率
dmesg | grep -i "Xid" | awk '{print $NF}' | sort | uniq -c | sort -rn
```

**实践规则**：
- Xid 63 出现次数 < 某阈值（如 20 次/天）→ 继续监控
- Xid 63 增长速率加快 → 提前更换节点
- Xid 48/79 → **立即下线**，不接受任何妥协

---

## 三、PCIe 链路诊断

```bash
# 查看 GPU 拓扑（NVLink/P2P 关系）
nvidia-smi topo -m

# 检查 PCIe 协商速率和宽度
lspci -vvv -s $(nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader | head -1) | grep -i "lnksta"

# 期望看到类似：
# LnkSta: Speed 16GT/s (ok), Width x16 (ok)
# 如果 Speed 或 Width 不达标，说明 PCIe 链路降级
```

**PCIe 速率速查**：

| 代际 | 单通道带宽 | x16 带宽 |
|---|---|---|
| PCIe 3.0 | ~1 GB/s | ~16 GB/s |
| PCIe 4.0 | ~2 GB/s | ~32 GB/s |
| PCIe 5.0 | ~4 GB/s | ~64 GB/s |

A100 用 PCIe 4.0 x16，H100 SXM 走 NVLink（900 GB/s），PCIe 版本走 PCIe 5.0。

---

## 四、监控体系深入

### DCGM 指标全景

```bash
# 安装 DCGM Exporter（Kubernetes 环境）
helm install dcgm-exporter nvdcgm/dcgm-exporter

# 核心指标列表
DCGM_FI_DEV_GPU_UTIL              # GPU 计算利用率
DCGM_FI_DEV_MEM_COPY_UTIL         # 显存带宽利用率
DCGM_FI_DEV_FB_USED               # 已用显存 (MiB)
DCGM_FI_DEV_FB_FREE               # 可用显存 (MiB)
DCGM_FI_DEV_GPU_TEMP              # GPU 温度
DCGM_FI_DEV_POWER_USAGE           # 实时功耗 (W)
DCGM_FI_DEV_ECC_SBE_VOL           # Single-bit Error 累计
DCGM_FI_DEV_ECC_DBE_VOL           # Double-bit Error 累计
DCGM_FI_DEV_RETIRED_PENDING       # 待退役行数
DCGM_FI_DEV_RETIRED_DBE           # 因 DBE 退役的行数
DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL # NVLink 总带宽
```

### 关键告警规则（Prometheus AlertManager 示例）

```yaml
groups:
  - name: gpu_alerts
    rules:
      # GPU 利用率异常低（训练时 < 30% 持续 10 分钟 → 可能 hang）
      - alert: GPULowUtilization
        expr: DCGM_FI_DEV_GPU_UTIL < 30 and on() DCGM_FI_DEV_GPU_UTIL > 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "GPU {{ $labels.gpu }} 利用率异常低，可能训练 hang"

      # ECC 错误增长
      - alert: GPUECCErrorGrowing
        expr: rate(DCGM_FI_DEV_ECC_DBE_VOL[1h]) > 0
        labels:
          severity: critical
        annotations:
          summary: "GPU {{ $labels.gpu }} 出现 Double Bit ECC 错误，需立即检查"

      # 温度过高
      - alert: GPUOverheat
        expr: DCGM_FI_DEV_GPU_TEMP > 83
        for: 5m
        labels:
          severity: warning

      # 显存泄漏检测（显存单调递增不释放）
      - alert: GPUMemoryLeak
        expr: predict_linear(DCGM_FI_DEV_FB_USED[30m], 3600) > DCGM_FI_DEV_FB_FREE
        labels:
          severity: warning
        annotations:
          summary: "GPU {{ $labels.gpu }} 显存可能泄漏，预计 1 小时内 OOM"
```

### 分布式追踪在训练场景的应用

训练任务的追踪链路：

```
用户提交任务
  → 调度器分配 GPU 节点
    → 容器拉取镜像
      → 数据加载 (DataLoader)
        → 模型初始化 / 加载 checkpoint
          → 前向传播 (Forward)
            → 反向传播 (Backward)
              → 梯度同步 (AllReduce)
                → 参数更新 (Optimizer Step)
```

**Jaeger 可以帮你定位**：
- 某个 step 特别慢 → 是 AllReduce 慢（网络瓶颈）还是计算慢（GPU 瓶颈）
- DataLoader 某些 epoch 突然变慢 → 存储 I/O 瓶颈
- 容器启动到开始训练耗时过长 → 镜像拉取或 checkpoint 加载慢

### eBPF 的独特价值

传统监控工具（DCGM、Prometheus）看到的是 **GPU 视角**，eBPF 看到的是 **系统调用和内核视角**：

```
eBPF 能观测的：
├── 网络层：每个 TCP 连接的 RTT、丢包率、重传
├── 文件 I/O：read/write 的延迟分布
├── 系统调用：futex 争用（NCCL 通信可能卡在这里）
├── 调度器：线程在 CPU 间迁移的频率
└── 内存：page fault 频率、NUMA 跨节点访问
```

**实战场景**：AllReduce 变慢 → DCGM 只能看到 GPU 利用率下降 → eBPF 抓到 `futex_wait` 耗时飙升 → 定位到是某个节点的网卡驱动问题。

---

## 五、故障排查决策树（速查）

```
训练任务报错或 hang
│
├── nvidia-smi 能否正常输出？
│   ├── 否 → GPU fallen off bus → Xid 79 → 物理故障，换卡
│   └── 是 ↓
│
├── dmesg | grep Xid 有输出？
│   ├── Xid 48/79/95 → 硬件故障，隔离节点
│   ├── Xid 63 → ECC 行退役，检查退役行数增长速率
│   └── 无 Xid ↓
│
├── GPU 温度 > 83°C？
│   ├── 是 → 散热问题，检查风扇/液冷/机房温度
│   └── 否 ↓
│
├── GPU 利用率 < 10% 但进程还在？
│   ├── 是 → 可能 hang 在通信，检查 NCCL 日志
│   └── 否 ↓
│
├── NCCL 报错？
│   ├── NVLink timeout → 检查 NVLink 拓扑和线缆
│   ├── Connection timeout → 检查网络 (IB/RoCE)
│   └── 否 ↓
│
├── OOM (Out of Memory)？
│   ├── 是 → 减小 batch size / 开启 gradient checkpointing / 用 ZeRO
│   └── 否 ↓
│
└── 数值异常 (NaN/Inf)？
    ├── 检查学习率、loss scaling、数据预处理
    └── 用 torch.autograd.detect_anomaly() 定位
```

---

以上是对每个模块从 **原理 → 工具 → 实操** 的补充。如果你在某个方向上想更深入（比如 NVLink 故障诊断、NCCL 调优、或者 Kubernetes 上的 GPU 调度策略），可以继续展开。
