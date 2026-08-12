---
title: Ceph RGW 对象存储入门
date: 2026-08-30 11:00:00
tags:
  - Ceph
  - RGW
  - 入门
categories:
  - Ceph 新手入门
---

**RGW（RADOS Gateway）** 提供 **S3 / Swift** 兼容 API，适合备份、静态资源、大数据。

## 部署 RGW

```bash
# 创建专用 pool
ceph osd pool create rgw_pool 64
ceph osd pool application enable rgw_pool rgw

# 部署 RGW 服务
ceph orch apply rgw myrgw --placement="3 ceph-node1 ceph-node2 ceph-node3" --port=8080

ceph orch ps | grep rgw
```

## 创建 S3 用户

```bash
radosgw-admin user create --uid=testuser --display-name="Test User"

# 输出 access_key / secret_key
```

## s3cmd / aws cli 测试

```bash
# aws cli 配置
aws configure set aws_access_key_id <access_key>
aws configure set aws_secret_access_key <secret_key>

# 上传
aws --endpoint-url http://ceph-node1:8080 s3 mb s3://mybucket
aws --endpoint-url http://ceph-node1:8080 s3 cp file.txt s3://mybucket/

# 列出
aws --endpoint-url http://ceph-node1:8080 s3 ls s3://mybucket/
```

## 与 MinIO/OSS 对比

| | Ceph RGW | 独立 MinIO |
|---|----------|------------|
| 后端 | RADOS | 自建 |
| 统一 | 与 RBD/CephFS 同集群 | 单独部署 |
| 运维 | 随 Ceph 升级 | 独立 |

## 典型场景

- GitLab/Velero 备份
- 日志/镜像归档
- S3 兼容应用迁移

## 反模式

- RGW 与 OSD 抢 CPU 无隔离
- 不启用 HTTPS（生产）
- 单 RGW 实例无负载均衡

下一篇：**ceph 命令行基础**。
