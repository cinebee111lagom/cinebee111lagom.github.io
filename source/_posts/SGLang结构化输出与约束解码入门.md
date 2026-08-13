---
title: SGLang 结构化输出与约束解码入门
date: 2026-09-05 10:45:00
tags:
  - SGLang
  - 结构化输出
  - 入门
categories:
  - SGLang 新手入门
---

SGLang 的重要卖点：**按 JSON Schema / 正则等约束生成**，提高可解析性。

## 为什么需要约束

| 只靠提示词 | 约束解码 |
|------------|----------|
| 可能多余文本 | 输出落在合法空间 |
| 字段缺失 | Schema 强制字段 |
| 后处理脆弱 | 减少解析失败 |

## JSON 场景（概念）

业务侧期望：

```json
{"intent": "refund", "order_id": "A123", "confidence": 0.92}
```

在 SGLang 中通过 **response_format / json_schema / 正则** 等机制约束（具体字段名随版本与后端 API 变化，查当前文档）。

## 适用场景

- Agent function calling 参数  
- 表单/工单信息抽取  
- 分类标签必须属于枚举集合  
- 配置生成必须合法 JSON  

## 实践建议

1. Schema 尽量简单、字段有限  
2. temperature 偏低  
3. 客户端仍做一次 JSON 校验兜底  
4. 失败重试要有上限  

## 反模式

- Schema 过于复杂导致极慢或拒答
- 约束与 chat template 冲突不排查
- 生产无监控「结构化失败率」

下一篇：**多 GPU**。
