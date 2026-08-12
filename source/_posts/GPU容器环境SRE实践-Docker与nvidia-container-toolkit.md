---
title: GPU 容器环境 SRE 实践：Docker 与 nvidia-container-toolkit
date: 2026-08-25 11:30:00
tags:
  - nvidia-smi
  - SRE
  - Docker
categories:
  - nvidia-smi SRE
---

容器是 GPU 推理与部分训练的主流交付形态，**宿主机 smi 正常 ≠ 容器内 smi 正常**。

## 栈结构

```
Host Driver → nvidia-container-toolkit → containerd/docker runtime → 容器内 libcuda
```

## 验收命令

```bash
# 宿主机
nvidia-smi

# Docker
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# 指定卡
docker run --rm --gpus '"device=0"' nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi -L
```

## 生产配置要点

| 项 | 建议 |
|----|------|
| runtime | 统一 nvidia 为 default runtime 或显式 `--gpus` |
| 镜像 | 基础镜像 CUDA 版本 ≤ 驱动支持版本 |
| cgroup | 容器 OOM 不应拖垮宿主机驱动 |
| 日志 | 容器 exit 后 smi 确认 GPU 释放 |

## 故障排查

| 现象 | 检查 |
|------|------|
| `could not select device driver` | toolkit 安装、daemon.json |
| 容器内无 GPU | `--gpus all`、NVIDIA_VISIBLE_DEVICES |
| 驱动版本不匹配 | 宿主机 `nvidia-smi` vs 镜像 CUDA |
| 性能差 | 是否 `--ipc=host`、是否 pin CPU |

```bash
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
```

## 与 K8s 关系

- K8s 节点同样依赖 container toolkit
- 裸 Docker 常用于 CI/CD GPU 构建机，也需纳入巡检

## 反模式

- 容器内自带驱动（NVIDIA 不支持此模式生产使用）
- 多租户共享 Docker 无 GPU 隔离
- 不限制 `--gpus` 导致单容器占满所有卡

容器 GPU 节点应纳入与裸金属相同的 **smi 巡检 + DCGM** 体系。
