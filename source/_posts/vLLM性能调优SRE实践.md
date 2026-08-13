---
title: vLLM 性能调优 SRE 实践
date: 2026-09-04 11:15:00
tags:
  - vLLM
  - SRE
  - 性能
categories:
  - vLLM SRE
---

生产调优以 **SLO 为导向**：先定 TTFT/吞吐目标，再改参数。

## 调优闭环

```
基线压测 → 定位瓶颈（GPU/排队/预填/解码）
        → 改一个旋钮 → 对比指标 → 固化配置
```

## 常见瓶颈与动作

| 瓶颈 | 信号 | 动作 |
|------|------|------|
| 排队 | waiting 高、GPU 未满 | 扩副本 |
| 显存 | OOM、util 顶满 | 降 len/seqs、量化 |
| 预填慢 | TTFT 高、长 prompt | 截断、前缀缓存、更大 GPU |
| 解码慢 | 长输出 | 限 max_tokens、推测解码（若支持） |
| 通信 | TP 多卡 util 不均 | 查 NVLink/拓扑 |

## 参数组合建议

| 目标 | 倾向 |
|------|------|
| 低延迟 | 较低 max_num_seqs、充足 GPU |
| 高吞吐 | 提高并发、吃满 GPU、连续批处理 |
| 成本 | 量化 + 合理 max_model_len |

## 前缀缓存

重复 system prompt / RAG 模板场景开启 `--enable-prefix-caching`，观察命中率。

## 压测规范

- 固定：模型、长度分布、采样  
- 输出：QPS、TTFT P99、token/s、错误率、GPU  
- 存档：命令、版本、结果 CSV  

## 反模式

- 同时改 5 个参数
- 用合成超短 prompt 估真实长上下文性能
- 为刷 GPU util 牺牲 P99

性能基线随 **每次大版本** 重测。
