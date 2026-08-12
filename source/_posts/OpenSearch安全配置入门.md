---
title: OpenSearch 安全配置入门
date: 2026-08-19 12:45:00
tags:
  - OpenSearch
  - 安全
categories:
  - OpenSearch 入门
---

生产 OpenSearch 必须启用 **Security 插件**：HTTPS、认证、角色权限。

## 默认安全（2.x）

Docker 生产镜像默认开启 Security，初始用户 `admin`：

```bash
curl -ku admin:Admin_12345! https://localhost:9200
```

## 用户与角色

```bash
# 创建角色
PUT /_plugins/_security/api/roles/app_reader
{
  "cluster_permissions": ["cluster_composite_ops_ro"],
  "index_permissions": [{
    "index_patterns": ["logs-*"],
    "allowed_actions": ["read", "search"]
  }]
}

# 创建用户并映射角色
PUT /_plugins/_security/api/internalusers/app_user
{
  "password": "StrongPass123!",
  "backend_roles": [],
  "attributes": {}
}

PUT /_plugins/_security/api/rolesmapping/app_reader
{
  "users": ["app_user"]
}
```

## Dashboards 登录

`opensearch_dashboards.yml`：

```yaml
opensearch.username: admin
opensearch.password: Admin_12345!
opensearch.ssl.verificationMode: none  # 生产应配 CA
```

## HTTPS

```yaml
# opensearch.yml
plugins.security.ssl.http.enabled: true
plugins.security.ssl.http.pemcert_filepath: certs/node.pem
plugins.security.ssl.http.pemkey_filepath: certs/node-key.pem
```

## 网络隔离

```
OpenSearch 9200 → 仅内网/VPC
Dashboards 5601 → Ingress + SSO 或 VPN
公网不暴露 9200
```

## 最小权限原则

| 账号 | 权限 |
|------|------|
| admin | 集群管理（限人数） |
| ingest | 写指定 index |
| reader | 读 Dashboards |
| snapshot | 备份专用 |

## 审计

Security 插件支持审计日志：谁、何时、访问哪个索引。

## 入门 Checklist

- [ ] 修改默认 admin 密码
- [ ] 应用独立账号，禁止共用 admin
- [ ] 启用 HTTPS
- [ ] 索引级权限控制
- [ ] 9200 不对公网

本地学习可 `DISABLE_SECURITY_PLUGIN=true`，**上线必须开启**。
