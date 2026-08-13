---
title: vLLM 新手学习路径与入门 Checklist
date: 2026-09-03 13:45:00
tags:
  - vLLM
  - 入门
  - 学习路径
categories:
  - vLLM 新手入门
---

## 推荐学习路径

```
第 1 周：概念 + 安装 + 离线推理 + API Server
  └─ 篇 1~5

第 2 周：模型/量化/多卡/采样/流式
  └─ 篇 6~10

第 3 周：LoRA/多模态/Docker/K8s/监控
  └─ 篇 11~15

第 4 周：调优/排查/对比/实战/Checklist
  └─ 篇 16~20
```

## 入门 Checklist

### 基础

- [ ] 说清 PagedAttention、Continuous Batching 的价值
- [ ] 成功 `pip install vllm` 或跑通官方镜像
- [ ] 离线 `LLM.generate` 跑通
- [ ] `vllm serve` + OpenAI SDK 对话成功

### 进阶

- [ ] 本地/HF 模型加载
- [ ] 至少试过一种量化（AWQ/GPTQ/FP8）
- [ ] 理解 TP 与多实例的区别
- [ ] 会调 temperature / max_tokens / stop

### 工程化

- [ ] Docker 启动并挂载模型目录
- [ ] 知道 `/metrics` 与 `/health`
- [ ] 会排查 OOM 与 model 名不匹配
- [ ] 完成简易 Chat 实战

## 配套练习

| 练习 | 技能点 |
|------|--------|
| opt-125m 冒烟 | 环境验证 |
| 7B Instruct 流式聊天 | API |
| AWQ 同模型对比显存 | 量化 |
| 2 卡 TP | 多 GPU |
| Docker Compose 部署 | 交付 |

## 推荐资源

- [vLLM 官方文档](https://docs.vllm.ai/)
- [Supported Models](https://docs.vllm.ai/en/latest/models/supported_models.html)
- [OpenAI API 参考](https://platform.openai.com/docs/api-reference)

## 延伸（后续可学）

- **vLLM SRE 系列**（HA、扩缩容、限流、多租户、告警）
- **nvidia-smi / DCGM** 配套看 GPU
- **K8s GPU 调度**、推理网关

---

**vLLM 新手入门系列 20 篇**完结，从零到能独立拉起 OpenAI 兼容推理服务。建议配合 GPU 监控系列一起实践。
