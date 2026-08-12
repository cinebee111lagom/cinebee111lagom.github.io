---
title: MinIO Console 与 mc 命令行入门
date: 2026-09-01 10:00:00
tags:
  - MinIO
  - mc
  - 入门
categories:
  - MinIO 新手入门
---

**Console** 适合可视化管理，**mc** 适合脚本与自动化。

## Console 功能

| 模块 | 作用 |
|------|------|
| Buckets | 创建、浏览、上传 |
| Users | 用户与密钥 |
| Policies | JSON 策略 |
| Monitoring | 基础指标 |
| Settings | 站点复制等 |

访问：`http://<host>:9001`，用 `MINIO_ROOT_USER/PASSWORD` 登录。

## mc 配置别名

```bash
mc alias set local http://localhost:9000 admin 'YourStrongPass123!'
mc alias list
```

## 常用 mc 命令

```bash
# Bucket
mc mb local/mybucket
mc ls local
mc ls local/mybucket

# 上传下载
mc cp file.txt local/mybucket/
mc cp local/mybucket/file.txt ./

# 递归
mc cp --recursive ./dir/ local/mybucket/backup/

# 删除
mc rm local/mybucket/file.txt
mc rm --recursive --force local/mybucket/old/

# 管理
mc admin info local
mc admin user list local
```

## 镜像同步

```bash
mc mirror local/srcbucket remote/dstbucket
```

## 脚本示例

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
mc cp --recursive /var/log/app/ local/logs/app-${DATE}/
```

## Console vs mc

| 场景 | 推荐 |
|------|------|
| 新手浏览 | Console |
| CI/CD | mc |
| 批量迁移 | mc mirror |
| 策略编辑 | Console 或 mc admin policy |

## 反模式

- 生产只用 Console 无自动化
- root 凭证写进脚本明文
- 不 `mc alias` 直接 curl 无签名

下一篇：**Bucket 管理**。
