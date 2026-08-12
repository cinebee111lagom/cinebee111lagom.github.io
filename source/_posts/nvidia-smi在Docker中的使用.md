---
title: nvidia-smi 在 Docker 中的使用
date: 2026-08-24 12:30:00
tags:
  - nvidia-smi
  - Docker
categories:
  - nvidia-smi 新手入门
---

容器内使用 GPU 需 NVIDIA Container Toolkit，容器内同样可运行 nvidia-smi。

## 安装 Container Toolkit

```bash
# Ubuntu
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## 运行容器

```bash
# 传统
docker run --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# 指定 GPU
docker run --gpus '"device=0,1"' nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# 全部 GPU
docker run --gpus all my-training-image:latest nvidia-smi
```

## 容器内 vs 宿主机

| 项 | 说明 |
|----|------|
| smi 输出 | 反映宿主机驱动 |
| 可见 GPU | 由 --gpus 限制 |
| 进程 PID | 容器内 PID ≠ 宿主机 |

宿主机查容器 GPU 进程：

```bash
nvidia-smi                    # 宿主机看真实 PID
docker top <container_id>
```

## docker-compose

```yaml
services:
  train:
    image: my-train:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

## 常见问题

| 问题 | 解决 |
|------|------|
| could not select device driver | 装 nvidia-container-toolkit |
| unknown flag: --gpus | 升级 Docker |
| 容器内无 smi | 镜像需基于 nvidia/cuda 或装驱动用户态库 |

Docker GPU = **宿主机驱动 + 容器 CUDA 库 + --gpus 分配**。
