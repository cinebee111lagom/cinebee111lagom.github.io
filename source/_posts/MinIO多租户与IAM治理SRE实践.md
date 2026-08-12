---
title: MinIO 多租户与 IAM 治理 SRE 实践
date: 2026-09-02 13:00:00
tags:
  - MinIO
  - SRE
  - IAM
categories:
  - MinIO SRE
---

多团队共用 MinIO 需 **桶隔离 + Policy + 配额 + 审计**。

## 租户模型

```
方案 A：每租户独立 bucket 前缀 + Policy
方案 B：独立 MinIO Tenant（K8s）
方案 C：独立集群（大租户）
```

## 命名规范

```
{tenant}-{env}-{purpose}
acme-prod-assets
acme-prod-backup
```

## IAM 流程

```
1. 租户申请 bucket + 权限模板
2. SRE 创建 bucket/quota/lifecycle
3. 创建 svcacct + 自定义 Policy
4. 交付 access-key（Vault/一次性）
5. 审计日志关联 tenant
```

## 配额

```bash
mc quota set alias/acme-prod-assets --size 1TB
mc quota info alias/acme-prod-assets
```

## 定期审计

- 孤儿 bucket（无 owner）
- 过期 access key
- public/anonymous 策略扫描

```bash
mc anonymous get alias/acme-prod-assets
```

## 反模式

- readwrite 模板给所有租户
- 无 quota 大租户吃满集群
- root key 分发

IAM 变更 **工单 + audit**。
