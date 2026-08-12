---
title: MinIO 故障演练与混沌工程
date: 2026-09-02 12:45:00
tags:
  - MinIO
  - SRE
  - 混沌工程
categories:
  - MinIO SRE
---

存储混沌需在 **staging** 验证 EC、LB、复制与 Runbook。

## 演练场景

| 场景 | 操作 | 期望 |
|------|------|------|
| 单节点 stop | systemctl stop minio | S3 可用 |
| 单盘 offline | 模拟拔盘 | heal 启动 |
| LB 后端全挂一半 | 仍读写 | 成功 |
| 网络分区 | iptables | 评估 split |
| 证书过期模拟 | 换无效 cert | 告警触发 |
| DR 切换 | DNS 切 DR | RTO 达标 |

## 业务验证

```bash
# 背景 warp mixed 持续压测
warp get --host=staging-s3 ... &
# 注入故障
# 检查错误率、P99
```

## 复制演练

```
暂停 prod→dr 网络 30min
恢复后 backlog 消化时间
```

## 成功标准

- P0 告警触达
- 无未文档化操作
- RTO/RPO 符合 SLA
- 应用无数据损坏（checksum）

## 频率

| 演练 | 周期 |
|------|------|
| 节点/盘 | 季 |
| DR 切换 | 半年 |
| 证书/配置 | 年 |

## 反模式

- prod 未通知混沌
- 演练不记录 RTO

报告归档 **SRE 季度复盘**。
