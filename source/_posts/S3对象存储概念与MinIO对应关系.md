---
title: S3 对象存储概念与 MinIO 对应关系
date: 2026-09-01 09:15:00
tags:
  - MinIO
  - S3
  - 入门
categories:
  - MinIO 新手入门
---

MinIO 遵循 **S3 语义**，理解 S3 概念即理解 MinIO 90%。

## 核心术语

| S3 概念 | 含义 | MinIO 对应 |
|---------|------|------------|
| Bucket | 桶，顶层容器 | 同名 |
| Object | 对象，key + 数据 | 同名 |
| Key | 对象路径名 | `photos/2024/a.jpg` |
| Region | 区域 | `us-east-1`（可自定义） |
| Endpoint | API 地址 | `http://minio:9000` |

## 扁平命名空间

```
s3://mybucket/path/to/file.txt
       ↑ bucket   ↑ key（含「目录」前缀，实为字符串）
```

S3 **无真实目录**，`/` 只是 key 前缀，Console 按前缀展示树形。

## 访问模型

```
Access Key + Secret Key → 签名请求 → MinIO 验证 → 读写 Object
```

与 AWS IAM 类似，MinIO 用 **用户 + Policy**。

## 常用 API 操作

| 操作 | API | mc 命令 |
|------|-----|---------|
| 建桶 | PutBucket | `mc mb` |
| 上传 | PutObject | `mc cp` |
| 下载 | GetObject | `mc cp` |
| 列表 | ListObjectsV2 | `mc ls` |
| 删除 | DeleteObject | `mc rm` |

## 一致性

MinIO 分布式提供 **read-after-write 一致性**（同 region 内）。

## 与文件系统区别

| | 文件系统 | 对象存储 |
|---|----------|----------|
| 修改 | 原地改 | 整对象替换 |
| 路径 | 真实 inode | key 字符串 |
| 适用 | 数据库、OS | 非结构化大数据 |

## 反模式

- 把 S3 当 POSIX 文件系统频繁小文件改写
- bucket 名含大写（S3 规范小写）
- 认为「文件夹」是真实目录

下一篇：**单机安装部署**。
