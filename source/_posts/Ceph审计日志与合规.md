---
title: Ceph 审计日志与合规
date: 2026-08-31 13:15:00
tags:
  - Ceph
  - SRE
  - 合规
categories:
  - Ceph SRE
---

金融、政企要求 **谁访问了什么数据、何时改了配置** 可追溯。

## 审计来源

| 来源 | 内容 |
|------|------|
| ceph-audit.log | 管理操作 |
| RGW access log | S3 API |
| Dashboard / API | 登录、配置 |
| kubectl / ansible | 变更工单关联 |

## 启用 RGW 访问日志

```bash
radosgw-admin zonegroup modify --rgw-zonegroup=default --log-sync=yes
# bucket logging 到指定 bucket
```

## 关键审计事件

- pool 创建/删除
- auth 变更
- osd crush 修改
- RGW user/bucket policy
- snapshot 删除

## 合规映射

| 要求 | 措施 |
|------|------|
| 最小权限 | cephx per-client |
| 变更审批 | 工单 + MR |
| 保留 | audit log ≥ 1 年 |
| 加密 | RGW TLS、at-rest 加密（可选） |

## 敏感操作

```bash
# 危险操作需双人复核
ceph osd pool delete ...
ceph osd crush ...
rados purge ...
```

## 反模式

- 无 audit 集中存储
- admin key 共享无法归因
- 删 pool 无审批

审计策略纳入 **等保/SOC2** 控制项。
