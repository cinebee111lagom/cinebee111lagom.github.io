---
title: MinIO 生命周期管理与过期策略入门
date: 2026-09-01 11:15:00
tags:
  - MinIO
  - 生命周期
  - 入门
categories:
  - MinIO 新手入门
---

**Lifecycle** 自动过期删除、转存储类，控制成本。

## 规则示例（JSON）

```json
{
  "Rules": [
    {
      "ID": "expire-logs-90d",
      "Status": "Enabled",
      "Filter": { "Prefix": "logs/" },
      "Expiration": { "Days": 90 }
    },
    {
      "ID": "clean-old-versions",
      "Status": "Enabled",
      "NoncurrentVersionExpiration": { "NoncurrentDays": 30 }
    }
  ]
}
```

```bash
mc ilm import local/mybucket < lifecycle.json
mc ilm ls local/mybucket
mc ilm export local/mybucket
```

## Console 配置

**Buckets → mybucket → Lifecycle → Add rule**

## 常见规则

| 规则 | 用途 |
|------|------|
| Prefix `tmp/` 7 天删除 | 临时文件 |
| 非当前版本 30 天删 | 版本控制桶清理 |
| 整桶 365 天 | 日志归档 |

## 与版本控制配合

开启 versioning 的 bucket **必须** 配 NoncurrentVersionExpiration，否则空间泄漏。

## 过渡（Transition）

MinIO 支持转 **MINIO_Standard / Reduced Redundancy** 等类（视版本），类似 S3 IA。

## 反模式

- 无 lifecycle 的日志 bucket
- Expiration Days=1 误配生产桶
- 不监控 bucket 容量增长

下一篇：**复制**。
