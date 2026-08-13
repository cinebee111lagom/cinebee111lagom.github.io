---
title: SGLang 模型制品管理与供应链安全
date: 2026-09-06 12:30:00
tags:
  - SGLang
  - SRE
  - 供应链
categories:
  - SGLang SRE
---

模型是生产关键制品，应按 **不可变制品** 管理，而不是「临时从网上下一份」。

## 制品内容

| 对象 | 要求 |
|------|------|
| 权重目录 | 版本号 / digest |
| Tokenizer / 模板 | 与权重绑定 |
| 容器镜像 | 固定 tag + digest |
| 启动参数 | Config 版本化 |

## 流程

```
评测通过 → 写入制品库（对象存储/Registry）
        → checksum 校验
        → 同步到生产 PVC/节点缓存
        → 发布单引用 digest
```

## 安全

- 来源可信：内网镜像与模型仓库  
- 扫描：镜像 CVE、可疑文件  
- 权限：谁能上传生产模型  
- OFFLINE：生产节点限制外网  

## 回滚

- 保留上一稳定版权重与镜像  
- 回滚演练：切 digest 能在 RTO 内恢复  

## 反模式

- 生产 Pod 启动时现场 `huggingface download`  
- 只有「最新」没有 digest  
- 算法同学直接 SSH 改权重目录  

**发布单写清：模型 digest、镜像 digest、评测报告链接。**
