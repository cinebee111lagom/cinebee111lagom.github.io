---
title: SGLang 新手学习路径与入门 Checklist
date: 2026-09-05 13:45:00
tags:
  - SGLang
  - 入门
  - 学习路径
categories:
  - SGLang 新手入门
---

## 推荐学习路径

```
第 1 周：概念 + 安装 + Runtime/Server + 采样/流式
  └─ 篇 1~7

第 2 周：结构化 + 多卡/量化/多模态
  └─ 篇 8~11

第 3 周：Docker/K8s/监控/调优/对比
  └─ 篇 12~16

第 4 周：排查 + 实战 + 缓存 + Checklist
  └─ 篇 17~20
```

## 入门 Checklist

### 基础

- [ ] 说清 RadixAttention 与结构化生成的价值
- [ ] 安装成功并 `launch_server` 拉起
- [ ] OpenAI SDK 对话成功
- [ ] 会调 temperature / max_tokens

### 进阶

- [ ] 试过结构化/JSON 约束（按版本文档）
- [ ] 理解 TP 与多副本区别
- [ ] 固定 system prompt 并感知加速
- [ ] Docker 挂载本地模型启动

### 工程化

- [ ] 知道 metrics/健康检查
- [ ] 会排查 OOM 与 model 名不匹配
- [ ] 完成简易 Chat 实战

## 配套练习

| 练习 | 技能点 |
|------|--------|
| opt-125m 冒烟 | 环境 |
| 7B Instruct 流式聊天 | API |
| JSON 抽取小任务 | 结构化 |
| 2 卡 TP | 多 GPU |
| 固定 vs 随机 system 对比 TTFT | 缓存 |

## 推荐资源

- [SGLang 官方文档](https://docs.sglang.ai/)
- [SGLang GitHub](https://github.com/sgl-project/sglang)
- OpenAI API 参考（兼容调用）

## 延伸

- **SGLang SRE 系列**（HA、限流、多租户、告警）
- **vLLM 新手/SRE** 对照
- **nvidia-smi / DCGM** GPU 可观测

---

**SGLang 新手入门系列 20 篇**完结，从零到能独立拉起 OpenAI 兼容推理服务。建议与 vLLM 系列对照实践。
