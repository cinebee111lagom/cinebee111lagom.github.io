---
title: GPU 多节点集群批量运维与 Ansible 实践
date: 2026-08-25 13:45:00
tags:
  - nvidia-smi
  - SRE
  - Ansible
categories:
  - nvidia-smi SRE
---

GPU 集群规模上来后，**批量 smi 巡检、基线下发、驱动一致性** 必须自动化。

## 架构

```
Ansible Control
  → inventory: gpu_nodes（按 pool/a100/h100 分组）
  → playbooks: check / baseline / driver / collect
  → 输出 → Prometheus push / 日志 / 工单
```

## Inventory 示例

```ini
[gpu_train]
gpu-node-[01:32].internal

[gpu_infer]
infer-gpu-[01:16].internal

[gpu:vars]
ansible_user=ops
expected_gpu_count=8
driver_version=550.54.15
```

## 批量巡检 Playbook 片段

```yaml
- name: GPU smi health check
  hosts: gpu
  gather_facts: no
  tasks:
    - name: Run nvidia-smi
      command: nvidia-smi --query-gpu=index,name,driver_version,memory.used,temperature.gpu \
        --format=csv,noheader
      register: smi_out
      failed_when: smi_out.rc != 0

    - name: Check GPU count
      shell: nvidia-smi -L | wc -l
      register: gpu_count
      failed_when: gpu_count.stdout | int != expected_gpu_count | int

    - name: Check ECC uncorrected
      shell: |
        nvidia-smi --query-gpu=ecc.errors.uncorrected.aggregate.total \
          --format=csv,noheader | awk -F',' '{s+=$1} END {exit (s>0)?1:0}'
      register: ecc_check
      failed_when: ecc_check.rc != 0
```

## 常用批量操作

| 操作 | 方式 |
|------|------|
| 采集 smi -q | fetch 到 central 存储 |
| 下发 `-pm 1` | baseline playbook |
| 驱动升级 | rolling: serial=1 + cordon |
| XID 扫描 | script: dmesg \| grep Xid |

## 与 K8s 联动

```bash
# 从 K8s 生成 Ansible inventory
kubectl get nodes -l nvidia.com/gpu.present=true -o name | \
  sed 's|node/||' > /tmp/gpu_hosts
```

保证 K8s 标签与 Ansible 分组一致。

## 报告示例

```
POOL train: 32 nodes OK, 1 WARN (GPU3 temp 86C), 0 FAIL
POOL infer: 16 nodes OK
Driver drift: 0 nodes
```

## 反模式

- 手工 for 循环 ssh 无并发控制
- Ansible 无 `--serial 1` 做驱动滚动
- 巡检结果不入库，无法趋势分析

批量运维是 **nvidia-smi SRE 系列收官**：把单机 smi 技能扩展到 **集群级可观测与一致性**。
