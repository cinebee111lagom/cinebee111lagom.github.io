---
title: nvidia-smi SRE 上线 Checklist 与生产 Runbook
date: 2026-08-25 13:30:00
tags:
  - nvidia-smi
  - SRE
  - Runbook
categories:
  - nvidia-smi SRE
---

GPU 节点接入生产池前的 **上线 Checklist** 与 **日常 Runbook** 汇总。

## 上线 Checklist

### 硬件与驱动

- [ ] `nvidia-smi -L` 卡数与采购一致
- [ ] 驱动版本符合池基线
- [ ] `nvidia-smi topo -m` 已存档
- [ ] PCIe link gen/width 正常
- [ ] ECC 模式符合策略

### 基线

- [ ] 持久化模式已开启（若需要）
- [ ] 功耗策略已应用
- [ ] MIG profile 已 IaC 化（若适用）

### 容器 / K8s

- [ ] nvidia-container-toolkit 正常
- [ ] 测试 Pod `nvidia-smi` 成功
- [ ] allocatable GPU 数量正确
- [ ] 节点 taint/label 正确

### 监控与告警

- [ ] dcgm-exporter 指标入 Prometheus
- [ ] Grafana Dashboard 可看到该节点
- [ ] P0/P1 告警 + Runbook 链接
- [ ] smi 巡检 cron 或 Ansible 已覆盖

### 安全与文档

- [ ] SSH/网络 ACL 符合规范
- [ ] CMDB 录入序列号、型号、上架日期
- [ ] 压测 baseline 已归档

---

## 日常 Runbook

### 每日

- 自动巡检脚本 / DCGM 看板
- 关注 P0/P1 未恢复告警

### 每周

- 池容量周报（显存、利用率）
- 驱动版本漂移检查

### 变更

- 驱动/MIG/固件：滚动 + smi 验收
- 新租户：配额与队列评审

### 故障

| 症状 | 动作 |
|------|------|
| smi 失败 | 掉卡 Runbook |
| XID | dmesg → cordon → 重启/RMA |
| ECC uncorrected | 立即下线 |
| 显存满 | 进程治理 Runbook |

---

## 应急联系

```
GPU 硬件 RMA → 厂商 + 机房
平台调度     → K8s/Slurm on-call
网络 IB      → 网络 SRE
```

## 反模式

- Checklist 在 wiki 从未执行
- 新节点跳过压测直接进 prod
- Runbook 无负责人与升级路径

本 Checklist 应与 **nvidia-smi 新手入门** 第 20 篇学习路径配合：入门练技能，SRE 管生产。
