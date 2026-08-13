---
title: SGLang 核心概念：RadixAttention 与结构化生成
date: 2026-09-05 09:15:00
tags:
  - SGLang
  - 入门
categories:
  - SGLang 新手入门
---

理解 **RadixAttention** 和 **结构化生成**，才能明白 SGLang 的差异化优势。

## RadixAttention

多请求常共享相同前缀（system prompt、工具说明、固定模板）。SGLang 用基数树管理 KV Cache：

```
System Prompt ████████
User A 前缀共享 ↑
User B 前缀共享 ↑
仅后缀部分重新计算
```

| 收益 | 说明 |
|------|------|
| 更低 TTFT | 命中缓存时预填更快 |
| 更高吞吐 | 减少重复计算 |
| 多轮对话 | 历史前缀可复用 |

## Continuous Batching

与主流推理引擎类似：请求完成即插入新请求，GPU 尽量吃满。

## 结构化生成

SGLang 强调 **按语法/约束生成**，例如：

- JSON Schema
- 正则表达式
- 有限状态机约束的合法输出

适合 Agent 工具调用、表单抽取、API 参数生成。

## Runtime vs Server

| 模式 | 用途 |
|------|------|
| Python Runtime | 脚本、离线批处理、开发调试 |
| `sglang.launch_server` | 生产 HTTP 服务 |

## 反模式

- 每条请求 system prompt 都随机变化，缓存无法命中
- 把结构化生成当成「提示词里写一下 JSON」而不用约束
- 只比单请求延迟，忽略高并发前缀复用收益

下一篇：**安装与环境准备**。
