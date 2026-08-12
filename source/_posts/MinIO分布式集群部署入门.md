---
title: MinIO 分布式集群部署入门
date: 2026-09-01 09:45:00
tags:
  - MinIO
  - 分布式
  - 入门
categories:
  - MinIO 新手入门
---

MinIO 分布式用 **纠删码（Erasure Code）** 实现冗余，节点+盘位需满足 erasure set 规则。

## Erasure Set 规则

```
至少 2 节点，每节点至少 1 块盘
常见：4 节点 × 4 盘 = 16 drives per set
容忍：EC:4 可损 4 块盘（视配置）
```

具体以 [MinIO 文档](https://min.io/docs/minio/linux/operations/install-deploy-manage/deploy-minio-multi-node-multi-drive.html) 为准。

## 四节点示例

每台节点 4 块数据盘：

```bash
# 在 node1 执行（需能解析 node1~4）
export MINIO_ROOT_USER=admin
export MINIO_ROOT_PASSWORD='YourStrongPass123!'

minio server \
  http://node{1...4}/data/minio{1...4} \
  --console-address ":9001"
```

URL 格式：`http://host/diskpath`

## 启动后验证

```bash
mc alias set myminio http://node1:9000 admin 'YourStrongPass123!'
mc admin info myminio
```

输出应显示 **4 nodes, 16 drives, erasure coding**。

## 负载均衡

生产前加 **Nginx/HAProxy** 统一 S3 Endpoint：

```
clients → LB:9000 → 所有 MinIO 节点
Console   → LB:9001
```

## 与单机区别

| | 单机 | 分布式 |
|---|------|--------|
| 冗余 | 无 | 纠删码 |
| 扩展 | 垂直 | 加节点/盘 |
| 生产 | 不推荐 | 推荐 |

## 反模式

- 节点数不满足 erasure set
- 各节点磁盘容量差异极大
- 无 LB 只连单节点

下一篇：**Console 与 mc**。
