---
title: GitLab 生产安全配置与访问控制
date: 2026-08-29 11:45:00
tags:
  - GitLab
  - SRE
  - 安全
categories:
  - GitLab SRE
---

GitLab 持有 **源码与密钥**，安全配置是 SRE 核心职责。

## 认证

```ruby
gitlab_rails['gitlab_signup_enabled'] = false
gitlab_rails['require_two_factor_authentication'] = true
gitlab_rails['password_authentication_enabled_for_git'] = false  # 强制 SSH/Token
```

## SSO（SAML/OAuth）

```ruby
gitlab_rails['omniauth_enabled'] = true
gitlab_rails['omniauth_providers'] = [
  {
    "name" => "openid_connect",
    ...
  }
]
```

禁用本地 admin 日常使用，break-glass 存保险库。

## 网络

| 层 | 措施 |
|----|------|
| LB | TLS 1.2+、WAF |
| Firewall | 仅 443/22（22 限堡垒机） |
| Internal | Gitaly/PG 不暴露公网 |

## API / Token 治理

- Personal Access Token **过期时间**强制
- Group Access Token 替代长期 PAT
- Audit events 记录 token 创建

## 审计

**Admin → Monitoring → Audit events**

接入 SIEM，告警：

- 权限提升
- 保护分支规则变更
- CI Variable 修改

## 依赖扫描

启用 **Security scanning**（EE）或 CI 集成 Trivy/SAST。

## 反模式

- Shared Runner 跑 fork 且 secrets 未保护
- 公网暴露 5050 Registry 无认证
- 2FA 可选

安全配置进 **上线 Checklist**，年度渗透测试。
