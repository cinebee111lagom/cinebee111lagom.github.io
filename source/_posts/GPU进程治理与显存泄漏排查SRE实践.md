---
title: GPU 进程治理与显存泄漏排查 SRE 实践
date: 2026-08-25 10:30:00
tags:
  - nvidia-smi
  - SRE
  - 进程
categories:
  - nvidia-smi SRE
---

「显存满了但没有作业」是 GPU 值班高频问题，**nvidia-smi 进程视图**是第一步。

## 诊断命令

```bash
# 计算进程与显存
nvidia-smi
nvidia-smi pmon -c 1

# 结构化查询
nvidia-smi --query-compute-apps=gpu_bus_id,pid,process_name,used_gpu_memory \
  --format=csv

# 图形进程（若有桌面/可视化）
nvidia-smi --query-gpu=index --format=csv,noheader | while read i; do
  nvidia-smi -i $i --query-compute-apps=pid,process_name,used_gpu_memory --format=csv
done
```

## 常见问题类型

| 现象 | 原因 | 处理 |
|------|------|------|
| 僵尸 Python/C++ 进程 | 作业异常退出未释放 CUDA | kill -9 + 验证 smi |
| 多进程占同一卡 | 未设 CUDA_VISIBLE_DEVICES | 调度层限制 |
| 容器退出 GPU 未释放 | 未用 nvidia runtime | 检查 container toolkit |
| 显存缓慢增长 | 泄漏 | 抓进程 + 联系开发 |

## 治理策略

```bash
# 查找占显存 Top 进程
nvidia-smi --query-compute-apps=pid,used_gpu_memory,process_name \
  --format=csv,noheader | sort -t, -k2 -nr | head

# 安全 kill（确认 PID 与作业归属）
kill -15 <pid> && sleep 5 && nvidia-smi
```

K8s 环境优先 `kubectl delete pod`，避免直接 kill 宿主机 PID 误伤。

## 预防

- 作业超时 + 自动清理（Slurm/K8s activeDeadlineSeconds）
- 共享节点禁止交互式长期占卡
- 定期 cron：`无对应业务标签的 GPU 进程 → 告警`

## Runbook 摘要

1. `nvidia-smi` 看 Used / Processes
2. 确认 PID 归属（ps、K8s、Slurm）
3. 协调或 kill → 再次 smi 确认释放
4. 若仍占用：重启 nvidia-persistenced 或节点 reboot（变更单）

## 反模式

- 不查进程直接 reboot 节点
- 生产节点开放 root 给全员 kill
- 无审计记录谁释放了哪张卡

进程治理规范应写入 **租户 GPU 使用公约**。
