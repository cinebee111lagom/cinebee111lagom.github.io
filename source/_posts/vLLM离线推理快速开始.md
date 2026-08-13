---
title: vLLM 离线推理快速开始
date: 2026-09-03 09:45:00
tags:
  - vLLM
  - 推理
  - 入门
categories:
  - vLLM 新手入门
---

用 Python API 跑通 **第一条生成**，是入门最短路径。

## 最小示例

```python
from vllm import LLM, SamplingParams

prompts = [
    "你好，请用一句话介绍 Kubernetes。",
    "什么是 SRE？",
]

sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    max_tokens=128,
)

llm = LLM(model="facebook/opt-125m")  # 换成你的模型
outputs = llm.generate(prompts, sampling_params)

for out in outputs:
    print(out.prompt)
    print(out.outputs[0].text)
    print("---")
```

## LLM 常用参数

| 参数 | 含义 |
|------|------|
| model | HF 模型名或本地路径 |
| tensor_parallel_size | 多卡切分 |
| max_model_len | 最大上下文 |
| dtype | auto / float16 / bfloat16 |
| gpu_memory_utilization | 0.0~1.0 |
| trust_remote_code | 部分自定义模型需要 |

```python
llm = LLM(
    model="/models/Qwen2.5-7B-Instruct",
    dtype="bfloat16",
    max_model_len=4096,
    gpu_memory_utilization=0.85,
)
```

## 输出结构

```
RequestOutput
  ├── prompt
  └── outputs[]  # CompletionOutput: text, token_ids, finish_reason
```

## 本地模型路径

```bash
# 目录需含 config.json、tokenizer、权重
LLM(model="/data/models/Llama-3.1-8B-Instruct")
```

## 反模式

- 第一次就加载 70B 导致 OOM
- temperature=0 却抱怨「没创意」
- 不设 max_tokens 导致意外超长

下一篇：**OpenAI 兼容 API Server**。
