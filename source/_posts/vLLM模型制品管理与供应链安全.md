---
title: vLLM 模型制品管理与供应链安全
date: 2026-09-04 12:15:00
tags:
  - vLLM
  - SRE
  - 供应链
categories:
  - vLLM SRE
---

模型是推理的「制品」，需像容器镜像一样 **版本、校验、晋升**。

## 制品目录规范

```
/models/
  Qwen2.5-7B-Instruct/
    v1/   # 不可变快照
    v2/
  current -> v2
```

或对象存储 + 节点缓存：

```
s3://llm-models/Qwen2.5-7B-Instruct/sha256-xxx/
```

## 晋升流水线

```
下载/训练产出 → 校验 checksum
             → 评测集门禁
             → 同步到 prod 模型仓
             → 更新 Deployment 挂载/路径
             → 观察期
```

## 校验

```bash
sha256sum -c model.sha256
# 或 huggingface 提供的 etag/commit 钉扎
```

生产 `HF_HUB_OFFLINE=1`，只读已晋升制品。

## 权限

| 角色 | 权限 |
|------|------|
| 算法 | 写 staging 仓 |
| SRE | 晋升 prod、回滚 |
| 运行时 | 只读挂载 |

## 回滚

保留上一版本路径至少 N 天；一键改 symlink/PVC subPath 并滚动。

## 反模式

- 生产直接 `model=org/name` 浮动 latest
- 无 checksum
- 评测未过就全量切流量

模型变更视为 **生产变更单**。
