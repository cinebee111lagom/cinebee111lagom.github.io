---
title: vLLM 常见问题与排查
date: 2026-09-03 13:00:00
tags:
  - vLLM
  - 排查
  - 入门
categories:
  - vLLM 新手入门
---

推理值班高频问题与 **第一步动作**。

## CUDA OOM

| 排查 | 动作 |
|------|------|
| 模型太大 | 量化 / 增 TP / 换小模型 |
| max_model_len 过大 | 降到业务所需 |
| 利用率过高 | `--gpu-memory-utilization 0.8` |
| 并发过高 | 降 `max_num_seqs` |

```bash
nvidia-smi
# 看是否有其它进程占卡
```

## 模型加载失败

- 权重不完整  
- 架构不支持  
- `trust_remote_code` 未开  
- HF token 无效（gated）  

## API 404 / model not found

`model` 字段必须与启动名或 `--served-model-name` 一致。

```bash
curl http://localhost:8000/v1/models
```

## 输出乱码 / 不遵循对话格式

- 应用 chat 接口而非 completions  
- chat template 不匹配  
- stop 词不对  

## 极慢

- 实际跑在 CPU（cuda unavailable）  
- PCIe 多卡通信差  
- 磁盘在加载/换页  
- 队列打满  

## 排查顺序

```
1. nvidia-smi / 健康检查
2. 日志里 OOM、NCCL、下载错误
3. /v1/models 与请求 model 名
4. 降 max_model_len 与并发复现
5. 换小模型验证环境
```

## 反模式

- 不看日志反复重启
- 生产直接拉最新镜像无回滚点

下一篇：**与 Transformers、TGI、Ollama 对比**。
