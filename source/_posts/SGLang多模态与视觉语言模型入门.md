---
title: SGLang 多模态与视觉语言模型入门
date: 2026-09-05 11:30:00
tags:
  - SGLang
  - 多模态
  - 入门
categories:
  - SGLang 新手入门
---

SGLang 支持部分 **VLM**，用于看图问答与文档理解。

## 能力概览

| 场景 | 说明 |
|------|------|
| 图片描述 | 商品图、截图 |
| 视觉问答 | 图表、界面 |
| 文档理解 | 扫描件/截图文字相关 |

以官方支持模型列表为准。

## OpenAI 风格调用（示意）

```python
from openai import OpenAI
import base64

client = OpenAI(base_url="http://localhost:30000/v1", api_key="EMPTY")

with open("img.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

resp = client.chat.completions.create(
    model="your-vlm-model",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "描述图片内容"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ],
    }],
    max_tokens=256,
)
print(resp.choices[0].message.content)
```

## 运维注意

- 图片会额外占显存与预填时间  
- 控制分辨率与并发  
- 纯文本模型不要塞 image_url  

## 反模式

- 原图 4K 无压缩打满显存
- 假设所有 VLM 字段完全一致
- 多模态与文本高并发混部无隔离

下一篇：**Docker 部署**。
