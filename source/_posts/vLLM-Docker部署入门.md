---
title: vLLM Docker 部署入门
date: 2026-09-03 12:00:00
tags:
  - vLLM
  - Docker
  - 入门
categories:
  - vLLM 新手入门
---

生产常用 **官方镜像** 跑 OpenAI Server，便于版本锁定与交付。

## 官方镜像示例

```bash
docker run --gpus all --shm-size=8g \
  -p 8000:8000 \
  -v /models:/models \
  -e HF_TOKEN=$HF_TOKEN \
  vllm/vllm-openai:latest \
  --model /models/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --gpu-memory-utilization 0.90
```

## docker-compose 片段

```yaml
services:
  vllm:
    image: vllm/vllm-openai:v0.6.0
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
    ports:
      - "8000:8000"
    volumes:
      - /data/models:/models
    shm_size: "8gb"
    command:
      - --model
      - /models/Qwen2.5-7B-Instruct
      - --host
      - 0.0.0.0
```

## 关键点

| 项 | 说明 |
|----|------|
| `--gpus all` | 需要 NVIDIA Container Toolkit |
| `shm-size` | 多进程/多卡过小会挂 |
| 挂载模型 | 避免每次拉 HF |
| 镜像 tag | 生产 pin 版本，勿长期 latest |

## 健康检查

```bash
curl -f http://localhost:8000/health || exit 1
curl http://localhost:8000/v1/models
```

## 反模式

- 容器内现场下载 70B 无缓存卷
- shm 默认 64MB 导致神秘崩溃
- 把 HF_TOKEN 写进镜像层

下一篇：**Kubernetes 入门**。
