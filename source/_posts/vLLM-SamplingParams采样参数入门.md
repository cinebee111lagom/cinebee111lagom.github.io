---
title: vLLM SamplingParams 采样参数入门
date: 2026-09-03 11:00:00
tags:
  - vLLM
  - 采样
  - 入门
categories:
  - vLLM 新手入门
---

生成质量很大程度取决于 **采样参数**，不是只换模型。

## 常用参数

```python
from vllm import SamplingParams

params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    top_k=50,
    max_tokens=512,
    presence_penalty=0.0,
    frequency_penalty=0.0,
    stop=["</s>", "用户:"],
    n=1,
)
```

## 参数含义

| 参数 | 作用 |
|------|------|
| temperature | 越高越随机；0 近乎贪心 |
| top_p | 核采样，累计概率截断 |
| top_k | 只从概率最高的 k 个选 |
| max_tokens | 最多生成 token 数 |
| stop | 遇到即停 |
| n | 每个 prompt 生成几条 |
| seed | 可复现（配合合适设置） |

## 场景推荐

| 场景 | 建议 |
|------|------|
| 代码/提取/分类 | temperature 0~0.2 |
| 客服问答 | 0.3~0.7 |
| 创意写作 | 0.8~1.2 |
| 严格格式 JSON | 低温 + 明确 prompt/约束 |

## API 中对应字段

```json
{
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 512,
  "stop": ["\n\n"]
}
```

## 反模式

- temperature 与 top_p 同时极端拉满
- max_tokens 过大拖垮吞吐
- 不用 stop，模型喋喋不休

下一篇：**流式输出与 Chat Template**。
