---
title: SGLang 量化推理入门
date: 2026-09-05 11:15:00
tags:
  - SGLang
  - 量化
  - 入门
categories:
  - SGLang 新手入门
---

量化降低权重精度，**省显存、提吞吐**，可能略损质量。

## 常见方向

| 方案 | 说明 |
|------|------|
| FP8 | 新卡友好 |
| INT4/AWQ/GPTQ | 显存紧张常用 |
| BF16/FP16 | 质量基线 |

具体 `--quantization` 可选值以当前 SGLang 版本文档为准。

## 启动示例（示意）

```bash
python -m sglang.launch_server \
  --model-path /models/Qwen2.5-7B-Instruct-AWQ \
  --quantization awq \
  --host 0.0.0.0 \
  --port 30000
```

## 选型

```
显存充足、要最好质量 → BF16/FP16
24GB 跑更大模型     → AWQ/GPTQ/INT4
Hopper/Ada 追吞吐   → FP8
```

## 验证质量

- 固定评测集对比未量化版本  
- 看关键业务：抽取准确率、工具调用成功率  
- 不要只看 token/s  

## 反模式

- 未量化权重却指定量化类型
- 把量化当无损
- 不记录量化配置导致环境不一致

下一篇：**多模态**。
