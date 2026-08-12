---
title: MinIO 版本控制与对象锁入门
date: 2026-09-01 11:00:00
tags:
  - MinIO
  - 版本控制
  - 入门
categories:
  - MinIO 新手入门
---

**版本控制** 保留对象历史版本；**对象锁** 防误删（WORM 合规）。

## 开启版本控制

```bash
mc version enable local/mybucket
mc version info local/mybucket
```

上传同名 key 会生成新版本，删除默认加 **delete marker**。

## 列出/恢复版本

```bash
mc ls --versions local/mybucket/file.txt
mc cp --version-id <vid> local/mybucket/file.txt ./restored.txt
```

## 删除指定版本

```bash
mc rm --version-id <vid> local/mybucket/file.txt
mc rm --versions --recursive local/mybucket/old/
```

## 对象锁（Object Lock）

需 bucket 创建时启用（或版本开启后配置 retention）：

```bash
mc retention set --default governance 30d local/mybucket
mc retention info local/mybucket/doc.pdf
```

| 模式 | 说明 |
|------|------|
| governance | 管理员可 override |
| compliance | 不可删改至到期 |

## 适用场景

| 场景 | 功能 |
|------|------|
| 误删恢复 | versioning |
| 合规归档 | object lock |
| 备份 | versioning + lifecycle |

## 反模式

- 全 bucket 开版本无 lifecycle（空间暴涨）
- compliance 锁测试数据
- 不知 delete marker 导致「删了还在」

下一篇：**生命周期**。
