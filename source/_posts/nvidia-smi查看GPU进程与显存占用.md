---
title: nvidia-smi 查看 GPU 进程与显存占用
date: 2026-08-24 10:15:00
tags:
  - nvidia-smi
  - 进程
categories:
  - nvidia-smi 新手入门
---

「谁占了我的 GPU」是运维最高频问题之一。

## 默认输出中的进程

```bash
nvidia-smi
# 底部 Processes 段列出 PID、进程名、显存
```

## pmon 进程监控

```bash
nvidia-smi pmon -c 1         # 采样 1 次
nvidia-smi pmon -s u -d 1    # 持续，显示利用率
```

输出列：GPU、PID、类型、SM%、mem%、enc%、dec%、命令。

## 查询计算进程

```bash
nvidia-smi --query-compute-apps=gpu_bus_id,pid,process_name,used_gpu_memory \
  --format=csv

nvidia-smi pids                     # 简要 PID 列表（部分版本）
```

## 按 GPU 过滤

```bash
nvidia-smi -i 0 --query-compute-apps=pid,process_name,used_gpu_memory --format=csv
```

## 查找并结束进程

```bash
# 确认进程
ps -p 123456 -o pid,user,cmd

# 优雅结束
kill 123456
kill -9 123456    # 慎用

# 再次确认显存释放
nvidia-smi
```

## 僵尸占用

进程已杀但显存未释放：

```bash
# 检查是否还有进程
nvidia-smi --query-compute-apps=pid --format=csv,noheader

# 最后手段（会中断该 GPU 所有任务）
sudo nvidia-smi --gpu-reset -i 0
```

## Docker/K8s 环境

宿主机 PID 对应容器：

```bash
# 找容器
cat /proc/123456/cgroup | grep docker
crictl ps | grep 123456
kubectl get pods -A -o wide | grep <node>
```

## 多用户场景

```bash
ps -p 123456 -o user=     # 看谁的任务
```

进程排查：**smi 看 PID → ps 看命令 → 协调用户或 kill**。
