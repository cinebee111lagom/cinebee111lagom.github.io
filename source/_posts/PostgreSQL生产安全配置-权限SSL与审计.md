---
title: PostgreSQL 生产安全配置：权限、SSL 与审计
date: 2026-08-15 11:45:00
tags:
  - PostgreSQL
  - 安全
categories:
  - PostgreSQL SRE
---

PostgreSQL 安全遵循最小权限、传输加密、审计可追溯。

## 角色与权限

```sql
-- 应用账号：仅 DML
CREATE ROLE app_user LOGIN PASSWORD 'strong_pass';
GRANT CONNECT ON DATABASE mydb TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;

-- 只读账号
CREATE ROLE readonly LOGIN PASSWORD 'read_pass';
GRANT pg_read_all_data TO readonly;
```

禁止：
- 应用使用 `superuser`
- `trust` 认证
- 公网暴露 5432

## pg_hba.conf

```
# TYPE  DATABASE  USER     ADDRESS         METHOD
hostssl  all       all      10.0.0.0/8      scram-sha-256
host     all       all      0.0.0.0/0       reject
```

## SSL/TLS

```ini
ssl = on
ssl_cert_file = '/etc/ssl/certs/server.crt'
ssl_key_file = '/etc/ssl/private/server.key'
ssl_min_protocol_version = 'TLSv1.2'
```

客户端：`sslmode=verify-full` + CA 证书。

## 审计

### pgAudit（推荐）

```ini
shared_preload_libraries = 'pgaudit'
pgaudit.log = 'write, ddl, role'
pgaudit.log_catalog = off
```

### 原生日志

```ini
log_statement = 'ddl'        # 或 'mod' / 'all'
log_connections = on
log_disconnections = on
```

## 网络隔离

```
App VPC → Security Group → PostgreSQL（仅内网）
管理访问 → Bastion / VPN
```

## 敏感数据

- 列级加密（application 层）
- `pgcrypto` 扩展哈希/加密
- 备份加密（pgBackRest `repo1-cipher-type`）

## 检查清单

- [ ] 无 superuser 远程登录
- [ ] scram-sha-256 认证
- [ ] SSL 强制（生产）
- [ ] pgAudit 或等效审计
- [ ] 定期权限 review
- [ ] 密码轮换策略

安全基线应纳入上线 Checklist 与合规扫描。
