---
title: vLLM SRE 上线 Checklist 与生产 Runbook
date: 2026-09-04 13:30:00
tags:
  - vLLM
  - SRE
  - Runbook
categories:
  - vLLM SRE
---

## 上线 Checklist

### 架构

- [ ] 模型/卡型/TP/副本策略已文档化
- [ ] 小模型多副本或大模型恢复路径明确
- [ ] 网关鉴权 + 限流就绪

### 配置

- [ ] 启动参数基线入库（Git）
- [ ] max_model_len / max_num_seqs 经压测
- [ ] api-key / Secret 非明文仓库

### 模型

- [ ] 制品 checksum 校验
- [ ] 生产 OFFLINE，不临时下载
- [ ] 回滚版本路径可用

### 监控

- [ ] /metrics 可刮取
- [ ] TTFT/队列/GPU 面板
- [ ] P0/P1 告警 + Runbook 链接

### 验收

- [ ] 黄金用例通过
- [ ] 流式正常
- [ ] 压测达 SLO 90% 以上

---

## 日常 Runbook

| 频率 | 动作 |
|------|------|
| 每日 | 看 P0/P1、排队、GPU OOM |
| 每周 | 利用率与成本、慢请求 Top |
| 每月 | 密钥轮换、镜像 CVE |
| 每季 | 故障演练、基线重压测 |

## 应急

| 事件 | 动作 |
|------|------|
| 服务 Down | 重启/回滚镜像；切备池 |
| OOM 风暴 | 降并发 → 降 len → 扩容 |
| TTFT 飙升 | 查队列与长 prompt；扩容或 429 |
| 错误内容投诉 | 转算法；临时关相关模型路由 |

## 反模式

- Checklist 未完成接全量
- 应急只重启不留根因

配合 **vLLM 新手入门** 系列：入门会用，SRE 保稳。
