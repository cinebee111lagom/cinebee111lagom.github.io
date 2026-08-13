---
title: vLLM 多模态与视觉语言模型入门
date: 2026-09-03 11:45:00
tags:
  - vLLM
  - 多模态
  - 入门
categories:
  - vLLM 新手入门
---

部分 **VLM（Vision-Language Model）** 可在 vLLM 中推理，用于看图问答。

## 支持范围

以官方文档「Supported Models」为准，常见如 LLaVA、部分 Qwen-VL、Phi-3.5-vision 等（版本演进快）。

## OpenAI 风格图片输入（示意）

```python
from openai import OpenAI
import base64

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")

with open("cat.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

resp = client.chat.completions.create(
    model="llava-hf/llava-1.5-7b-hf",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "描述这张图片"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ],
    }],
    max_tokens=256,
)
print(resp.choices[0].message.content)
```

## 启动注意

```bash
vllm serve <vlm-model> \
  --max-model-len 4096 \
  --limit-mm-per-prompt image=1
```

多模态额外占显存，**并发与图片分辨率** 要保守设置。

## 适用场景

- 单据/截图理解
- 商品图描述
- 简单视觉问答

## 反模式

- 用纯文本模型硬塞 image_url
- 高清大图无缩放打满显存
- 假设所有多模态模型 API 字段完全一致

下一篇：**Docker 部署**。
