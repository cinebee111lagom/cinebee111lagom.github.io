---
title: MinIO 性能调优与基准测试 SRE 实践
date: 2026-09-02 11:30:00
tags:
  - MinIO
  - SRE
  - 性能
categories:
  - MinIO SRE
---

MinIO 性能取决于 **磁盘、网络、并发、对象大小**。

## 基准工具

```bash
# MinIO 官方 warp
warp mixed --host=s3.example.com --access-key=xxx --secret-key=yyy \
  --duration=5m --objects=10000 --obj.size=1MiB

# aws cli
aws --endpoint-url https://s3.example.com s3 cp big.bin s3://bench/ \
  --expected-size 1073741824
```

记录：**PUT/GET IOPS、吞吐、P99 延迟**。

## 调优清单

| 层 | 项 |
|----|-----|
| 磁盘 | NVMe、XFS、无 RAID5 写惩罚 |
| 网络 | 25G、jumbo frame 一致 |
| LB | least_conn、proxy_buffering off |
| 客户端 | multipart 并发、连接池 |
| 集群 | 节点/盘对称 |

## 对象大小策略

| 大小 | 建议 |
|------|------|
| < 1MB 海量 | 合并/压缩，或评估是否适合对象存储 |
| 1MB~1GB | MinIO 舒适区 |
| > 5GB | multipart 必开 |

## 性能回归

升级、换盘、改 EC 后 **重跑 warp baseline**。

## 反模式

- HDD 期望 SSD 延迟
- 单线程小文件压测否定架构
- Nginx 默认 1m body limit

报告含：**拓扑、版本、warp 命令、结果 CSV**。
