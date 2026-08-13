---
title: vLLM 模型加载与 HuggingFace 集成入门
date: 2026-09-03 10:15:00
tags:
  - vLLM
  - HuggingFace
  - 入门
categories:
  - vLLM 新手入门
---

vLLM 直接吃 **HuggingFace 格式** 权重（或本地同结构目录）。

## 三种来源

| 来源 | 示例 |
|------|------|
| HF Hub | `Qwen/Qwen2.5-7B-Instruct` |
| 本地路径 | `/models/Qwen2.5-7B-Instruct` |
| ModelScope 等 | 先下载到本地再加载 |

## 下载模型

```bash
# huggingface-cli
huggingface-cli download Qwen/Qwen2.5-7B-Instruct \
  --local-dir /models/Qwen2.5-7B-Instruct

# 或 snapshot_download
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("Qwen/Qwen2.5-7B-Instruct", local_dir="/models/Qwen2.5-7B-Instruct")
PY
```

## Instruct / Chat 模型

对话模型务必使用 **正确 chat template**。Server 模式通常自动套用 tokenizer 的 chat_template。

离线时可用：

```python
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(model)
messages = [{"role": "user", "content": "你好"}]
prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
```

## Gated 模型

Llama 等需：

1. HF 页面同意协议  
2. `HF_TOKEN` 或 `huggingface-cli login`

## 权重检查清单

- [ ] `config.json` 存在
- [ ] tokenizer 文件齐全
- [ ] 分片权重完整（无下载中断）
- [ ] 架构在 vLLM 支持列表中

## 反模式

- 把训练 checkpoint 残缺目录当完整模型
- Chat 模型当 base 直接补全，格式混乱
- 网络不稳时反复在线加载

下一篇：**量化推理**。
