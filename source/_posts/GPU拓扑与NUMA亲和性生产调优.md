---
title: GPU 拓扑与 NUMA 亲和性生产调优
date: 2026-08-25 10:45:00
tags:
  - nvidia-smi
  - SRE
  - NUMA
categories:
  - nvidia-smi SRE
---

错误 NUMA/PCIe 亲和会导致**多卡训练带宽腰斩**，上线前必须用 `nvidia-smi topo` 验收。

## 拓扑查看

```bash
nvidia-smi topo -m
numactl --hardware
lscpu | grep NUMA
```

`topo -m` 中 **NV#** 表示 NVLink，**PIX/PHB** 表示 PCIe 跳数，数字越小越好。

## 生产调优原则

| 场景 | 建议 |
|------|------|
| 单机 8 卡训练 | CPU 绑 NUMA 与 GPU 同 socket |
| 数据加载 | dataloader num_workers 绑本地 NUMA |
| 多机 | GPU Direct RDMA + IB 拓扑文档化 |

## 绑定示例

```bash
# 查看 GPU 0 的 NUMA 节点（因平台而异，结合 sysfs）
cat /sys/bus/pci/devices/$(nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader -i 0 | sed 's/00000000://' | tr ':. ' '_')/numa_node

# 训练启动绑 NUMA（示例）
numactl --cpunodebind=0 --membind=0 python train.py
```

## 验收 Checklist

- [ ] `topo -m` 已存档至节点 CMDB
- [ ] 8 卡 NVLink 全互联（若卡型支持）
- [ ] 压测带宽符合基线（nccl-tests / ib_write_bw）
- [ ] K8s CPUManager/Topology Manager 策略与裸金属一致

## 故障信号

- 多卡训练 step time 异常慢
- `nvidia-smi dmon` 显示 GPU util 低但 CPU 100%
- PCIe `link.gen` 未跑在最高代际

```bash
nvidia-smi --query-gpu=index,pcie.link.gen.current,pcie.link.width.current \
  --format=csv
```

## 反模式

- 不做 topo 文档，故障时无法判断硬件 vs 配置
- 虚拟机未 pin NUMA，宿主混部导致抖动
- 仅看 GPU util 不看 Host↔Device 拷贝瓶颈

拓扑信息应随 **节点上线 Runbook** 一并交付给调度与训练平台。
