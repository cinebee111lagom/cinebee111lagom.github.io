---
title: SGLang 采样参数与生成控制入门
date: 2026-09-05 10:15:00
tags:
  - SGLang
  - 采样
  - 入门
categories:
  - SGLang 新手入门
---

生成质量很大程度取决于 **采样参数**，不是只换模型。

## 常用参数

| 参数 | 作用 |
|------|------|
| temperature | 越高越随机；偏低更稳 |
| top_p | 核采样 |
| top_k | 截断候选 token |
| max_tokens / max_new_tokens | 最大生成长度 |
| stop | 停止词 |
| presence/frequency_penalty | 降低重复 |

## API 示例

```json
{
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 512,
  "stop": ["</s>"]
}
```

## 场景建议

| 场景 | 建议 |
|------|------|
| JSON/工具调用 | 低温 + 结构化约束 |
| 客服问答 | 0.3~0.7 |
| 创意写作 | 0.8~1.1 |
| 代码补全 | 0~0.3 |

## 与结构化生成配合

需要严格格式时：

1. 先把 temperature 降下来  
2. 再用 JSON Schema / regex 约束  
3. 不要只靠「请输出 JSON」提示词  

## 反模式

- temperature 与 top_p 同时极端
- max_tokens 过大拖垮吞吐与费用
- 不用 stop，模型说个没完

下一篇：**流式输出与多轮对话**。
