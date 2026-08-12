---
title: 阿里云 VPC 网络与安全组 SRE 实践
date: 2026-08-26 09:45:00
tags:
  - 阿里云
  - VPC
  - 网络
categories:
  - 阿里云资源 SRE
---

VPC 是云上网络隔离边界，SRE 需规划网段、路由与安全组。

## VPC 规划

```
prod-vpc:     10.0.0.0/16
  ├── az-a public:  10.0.1.0/24   (SLB/NAT)
  ├── az-a private: 10.0.10.0/24  (ECS/ACK)
  ├── az-b public:  10.0.2.0/24
  └── az-b private: 10.0.20.0/24

staging-vpc:  10.1.0.0/16
```

- 不同环境 **独立 VPC**
- 预留扩展空间，避免 /24 过小

## 子网与路由

| 类型 | 路由 |
|------|------|
| 公网子网 | 0.0.0.0/0 → NAT 网关 / IGW |
| 私网子网 | 0.0.0.0/0 → NAT（出网）；内网互访本地 |

## 安全组（最小权限）

```
sg-web:
  In:  443 from sg-slb
  Out: 8080 to sg-app

sg-app:
  In:  8080 from sg-web
  Out: 3306 to sg-rds, 6379 to sg-redis

sg-rds:
  In:  3306 from sg-app
  Out: deny all（默认）
```

**禁止** 0.0.0.0/0 开放 22/3306/6379。

## 网络 ACL（可选）

子网级额外防护，默认允许，异常流量 deny。

## 对等连接 / CEN

```
prod-vpc ←→ CEN ←→ dev-vpc
跨地域/跨账号互通，替代公网
```

## 检查清单

- [ ] 生产无公网 IP 直连数据库
- [ ] 安全组引用安全组 ID，非 CIDR 0.0.0.0/0
- [ ] NAT 网关高可用（多 AZ）
- [ ] 流日志（VPC Flow Log）开启
- [ ] DNS 私有域解析内网服务

网络问题是云上故障**最常见根因**，变更需评审。
