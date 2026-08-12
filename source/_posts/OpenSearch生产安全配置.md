---
title: OpenSearch 生产安全配置
date: 2026-08-20 11:30:00
tags:
  - OpenSearch
  - 安全
categories:
  - OpenSearch SRE
---

OpenSearch Security 插件提供认证、授权、TLS 与审计，生产必须正确配置。

## TLS 全链路

```yaml
plugins.security.ssl.transport.enabled: true
plugins.security.ssl.http.enabled: true
plugins.security.ssl.transport.pemcert_filepath: certs/node.pem
plugins.security.ssl.transport.pemkey_filepath: certs/node-key.pem
plugins.security.ssl.transport.pemtrustedcas_filepath: certs/root-ca.pem
plugins.security.ssl.http.pemcert_filepath: certs/node.pem
plugins.security.ssl.http.pemkey_filepath: certs/node-key.pem
```

节点间 transport 加密防窃听与中间人。

## 认证后端

| 后端 | 场景 |
|------|------|
| internal | 内置用户 DB |
| LDAP/AD | 企业目录 |
| SAML/OIDC | Dashboards SSO |

## RBAC 角色设计

```bash
PUT /_plugins/_security/api/roles/logs_reader
{
  "index_permissions": [{
    "index_patterns": ["logs-*"],
    "allowed_actions": ["read", "search"]
  }]
}

PUT /_plugins/_security/api/roles/logs_writer
{
  "index_permissions": [{
    "index_patterns": ["logs-*"],
    "allowed_actions": ["write", "create_index"]
  }]
}
```

| 账号 | 角色 |
|------|------|
| admin | all_access（限人数） |
| filebeat | logs_writer |
| dashboards-user | logs_reader |
| snapshot | snapshot_restore |

## 索引级权限

```json
"index_permissions": [{
  "index_patterns": ["app-logs-*"],
  "dls": "{\"term\": {\"env\": \"prod\"}}",
  "allowed_actions": ["read"]
}]
```

Document Level Security 限制可见文档。

## 审计日志

```yaml
plugins.security.audit.type: internal_opensearch
plugins.security.audit.config.disabled_rest_categories: NONE
```

## 网络

- 9200/9300 仅内网
- Dashboards 5601 经 Ingress + OAuth2
- 禁止公网暴露 transport 9300

## 检查清单

- [ ] 默认 admin 密码已改
- [ ] 应用独立账号
- [ ] TLS transport + http
- [ ] destructive_requires_name: true
- [ ] 审计开启
- [ ] 季度权限 review

安全基线纳入上线 Checklist，与 **Kafka/MySQL SRE** 凭证管理对齐。
