---
title: SGLang Docker 部署入门
date: 2026-09-05 11:45:00
tags:
  - SGLang
  - Docker
  - 入门
categories:
  - SGLang 新手入门
---

生产常用容器固化版本，挂载本地模型目录。

## 运行示例

```bash
docker run --gpus all --shm-size=32g \
  -p 30000:30000 \
  -v /data/models:/models \
  -e HF_HUB_OFFLINE=1 \
  lmsysorg/sglang:latest \
  python -m sglang.launch_server \
    --model-path /models/Qwen2.5-7B-Instruct \
    --host 0.0.0.0 \
    --port 30000 \
    --mem-fraction-static 0.85
```

镜像名/tag 以官方仓库为准，生产 **pin 版本**。

## compose 片段

```yaml
services:
  sglang:
    image: lmsysorg/sglang:v0.4.0
    ports:
      - "30000:30000"
    volumes:
      - /data/models:/models
    shm_size: "32gb"
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
    command:
      - python
      - -m
      - sglang.launch_server
      - --model-path
      - /models/Qwen2.5-7B-Instruct
      - --host
      - 0.0.0.0
      - --port
      - "30000"
```

## 要点

| 项 | 说明 |
|----|------|
| shm-size | 过小易莫名崩溃 |
| 模型卷 | 避免每次下载 |
| GPU toolkit | 需 NVIDIA Container Toolkit |
| OFFLINE | 生产禁止临时拉权重 |

## 健康检查

```bash
curl -f http://localhost:30000/v1/models
```

## 反模式

- 容器内现场下载 70B
- 使用 latest 无回滚点
- 把密钥写进镜像层

下一篇：**Kubernetes**。
