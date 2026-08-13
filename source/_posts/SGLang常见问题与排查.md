---
title: SGLang 常见问题与排查
date: 2026-09-05 13:00:00
tags:
  - SGLang
  - 排查
  - 入门
categories:
  - SGLang 新手入门
---

推理值班高频问题与 **第一步动作**。

## CUDA OOM

| 动作 | 说明 |
|------|------|
| 降 context-length | 减 KV |
| 降并发 | 减同时序列 |
| 降 mem-fraction | 留余量 |
| 量化 / 增 TP | 降单卡压力 |
| nvidia-smi | 查是否他进程占卡 |

## 加载失败

- 权重不完整  
- 架构不支持  
- HF token / gated  
- 磁盘空间不足  

## API model not found

```bash
curl http://localhost:30000/v1/models
```

请求里的 `model` 必须与启动名或 served-model-name 一致。

## 极慢

- 实际跑在 CPU  
- 前缀毫无复用  
- 队列打满  
- 磁盘在读权重/换页  
- TP 通信差  

## 结构化失败

- Schema 过严  
- temperature 过高  
- 版本不支持该约束后端  

## 排查顺序

```
1. nvidia-smi / 端口连通
2. 日志中 OOM、NCCL、下载错误
3. /v1/models 与请求 model
4. 降上下文与并发复现
5. 小模型验证环境
```

## 反模式

- 不看日志反复重启
- 生产无版本钉扎无法对比回归

下一篇：**实战 Chat 服务**。
