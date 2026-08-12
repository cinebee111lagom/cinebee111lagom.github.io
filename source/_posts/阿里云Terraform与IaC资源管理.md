---
title: 阿里云 Terraform 与 IaC 资源管理
date: 2026-08-25 13:30:00
tags:
  - 阿里云
  - Terraform
  - IaC
categories:
  - 阿里云资源 SRE
---

**Infrastructure as Code** 让阿里云资源可版本化、可审计、可重复部署。

## 为什么 IaC

| 收益 | 说明 |
|------|------|
| 一致性 | dev/staging/prod 同模板 |
| 审计 | Git 历史 = 变更记录 |
| 回滚 | revert commit + apply |
| 协作 | PR review 改基础设施 |

## Terraform 结构

```
terraform/
├── modules/
│   ├── vpc/
│   ├── ecs/
│   └── rds/
├── envs/
│   ├── dev/
│   ├── staging/
│   └── prod/
└── backend.tf   # OSS 远程 state
```

## Provider 配置

```hcl
terraform {
  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.220"
    }
  }
  backend "oss" {
    bucket = "tf-state-prod"
    prefix = "payment/"
    key    = "terraform.tfstate"
    region = "cn-hangzhou"
  }
}

provider "alicloud" {
  region = var.region
}
```

## 模块示例（VPC）

```hcl
module "vpc" {
  source     = "../../modules/vpc"
  name       = "${var.project}-vpc"
  cidr_block = "10.0.0.0/16"
  vswitches  = var.azs
  tags       = var.common_tags
}
```

## State 安全

```
- 远程 state 存 OSS，加密 + 版本
- state 锁（DynamoDB 等价：Tablestore 或 OSS 锁）
- 禁止本地 state 提交 Git
- 敏感 output 标记 sensitive
```

## CI/CD

```
PR → terraform plan → 评论 diff
merge main → terraform apply（需审批）
```

## 与 RAM 配合

```
CI 使用 RAM Role（OIDC/GitHub Actions）
禁止长期 AK 在流水线
```

## 漂移检测

```
定期 terraform plan -detailed-exitcode
Config 审计 vs 代码不一致告警
```

## Checklist

- [ ] 远程 state + 锁
- [ ] module 化 VPC/ECS/RDS
- [ ] Tag 统一变量
- [ ] plan 必过 PR
- [ ] prod apply 双人审批

IaC 与 **RAM 治理、Tag 规范** 是云治理铁三角。
