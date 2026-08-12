---
title: MinIO 新手学习路径与入门 Checklist
date: 2026-09-01 13:45:00
tags:
  - MinIO
  - 入门
  - 学习路径
categories:
  - MinIO 新手入门
---

## 推荐学习路径

```
第 1 周：概念 + 单机部署 + Console/mc
  └─ 篇 1~5

第 2 周：Bucket/用户/Policy + 上传下载
  └─ 篇 6~9

第 3 周：生命周期/复制/TLS + K8s
  └─ 篇 10~13

第 4 周：SDK/监控/EC + 对比/备份
  └─ 篇 14~18

第 5 周：排查 + Checklist 验收
  └─ 篇 19~20
```

## 入门 Checklist

### 基础

- [ ] 理解 Bucket/Object/S3 API
- [ ] 单机 MinIO 跑通，Console 可登录
- [ ] mc alias 配置成功
- [ ] 创建 bucket、上传下载文件

### 权限

- [ ] 创建非 root 用户 + 自定义 Policy
- [ ] 应用使用 svcacct，非 root

### 分布式（可选）

- [ ] 4 节点分布式部署
- [ ] mc admin info 显示 erasure set

### 集成

- [ ] aws cli 或 boto3 对接成功
- [ ] presigned URL 测试
- [ ] Prometheus 能 scrape metrics

### 运维

- [ ] lifecycle 规则配置
- [ ] TLS 启用（或 LB 终止）
- [ ] 完成一次 mc mirror 备份

## 配套练习

| 练习 | 技能点 |
|------|--------|
| 静态网站资源桶 | bucket + policy |
| Velero + MinIO | K8s 备份 |
| Python 上传脚本 | SDK |
| 版本误删恢复 | versioning |

## 推荐资源

- [MinIO 官方文档](https://min.io/docs/minio/linux/index.html)
- [MinIO Operator](https://github.com/minio/operator)
- [AWS S3 API 参考](https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html)

## 延伸（后续可学）

- **MinIO SRE 系列**（HA、告警、升级、安全）
- **Ceph RGW** 对比深化
- **数据湖** Iceberg + MinIO

---

**MinIO 新手入门系列 20 篇**完结，从零到能独立部署并使用 S3 兼容对象存储。建议配合 **Kubernetes**、**Velero** 实践。
