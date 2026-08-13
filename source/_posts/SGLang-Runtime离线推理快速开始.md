---
title: SGLang Runtime 离线推理快速开始
date: 2026-09-05 09:45:00
tags:
  - SGLang
  - 推理
  - 入门
categories:
  - SGLang 新手入门
---

用 Python Runtime 跑通 **第一条生成**，是最短入门路径。

## 最小示例

```python
from sglang import Engine

engine = Engine(model_path="facebook/opt-125m")

prompt = "Kubernetes is"
out = engine.generate(prompt, {"max_new_tokens": 64, "temperature": 0.7})
print(out)
```

API 细节随版本演进，以你安装版本文档为准；核心是 **Engine/Runtime + generate**。

## 常用加载参数（概念）

| 参数 | 含义 |
|------|------|
| model_path | HF 名或本地路径 |
| tp_size | Tensor Parallel 卡数 |
| dtype | auto / float16 / bfloat16 |
| context_length | 最大上下文 |
| mem_fraction_static | 显存占用比例 |

## 本地模型

```python
engine = Engine(model_path="/models/Qwen2.5-7B-Instruct")
```

目录需含 `config.json`、tokenizer 与完整权重。

## 批量

```python
prompts = ["介绍 SRE", "什么是 GitOps"]
# 批量接口名以版本文档为准
outs = engine.generate(prompts, {"max_new_tokens": 128})
```

## 反模式

- 第一次就加载超大模型导致 OOM
- 不设 max_new_tokens 生成过长
- 把 Chat 模型当 base 裸补全

下一篇：**OpenAI 兼容 Server**。
