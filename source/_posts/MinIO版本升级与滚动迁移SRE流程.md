---
title: MinIO 版本升级与滚动迁移 SRE 流程
date: 2026-09-02 10:45:00
tags:
  - MinIO
  - SRE
  - 升级
categories:
  - MinIO SRE
---

MinIO 升级需 **逐节点滚动**，保证 quorum 与 EC 可用。

## 升级前

- [ ] Release Notes Breaking Changes
- [ ] `mc admin info` 记录版本
- [ ] staging 同版本验证
- [ ] 备份 config + 关键 bucket manifest

## 裸金属滚动

```bash
# 每节点（LB 先 drain）
systemctl stop minio
# 替换二进制或拉新容器镜像
minio --version
systemctl start minio
curl http://localhost:9000/minio/health/ready
# 下一节点
```

## K8s Operator

```bash
kubectl set image tenant/minio-tenant minio=minio/minio:RELEASE.2024-xx-xx
kubectl rollout status statefulset/minio-tenant-pool-0 -n minio
```

按 Operator 文档 **pool 顺序** 升级。

## 验证

```bash
mc admin info alias
mc cp /dev/zero alias/testbucket/upgrade-test --size 1MiB
mc admin prometheus generate alias  # metrics 正常
```

## 回滚

- 保留上一版本二进制/镜像
- Operator 可 spec 回退 image tag
- 数据盘向前兼容，一般无需迁移

## 反模式

- 全节点同时 restart
- 跨多个 major 未测
- 升级窗口做大范围 lifecycle 变更

升级记录：**版本、节点顺序、问题**。
