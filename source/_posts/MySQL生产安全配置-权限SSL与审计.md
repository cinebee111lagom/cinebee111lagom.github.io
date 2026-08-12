---
title: MySQL 生产安全配置：权限、SSL 与审计
date: 2026-08-14 11:45:00
tags:
  - MySQL
  - 安全
categories:
  - MySQL SRE
---

数据库安全是 SRE **不可妥协**的底线。

## 账号最小权限

```sql
-- 应用账号：仅业务库 DML
CREATE USER 'app'@'10.0.%' IDENTIFIED BY 'strong_pass';
GRANT SELECT, INSERT, UPDATE, DELETE ON mydb.* TO 'app'@'10.0.%';

-- 只读账号
GRANT SELECT ON mydb.* TO 'readonly'@'10.0.%';
```

禁止：

- `root@%`
- 应用账号 `SUPER`、`FILE`、`SHUTDOWN`
- 空密码、弱密码

## SSL/TLS

```ini
require_secure_transport = ON
ssl_ca = /etc/mysql/ssl/ca.pem
ssl_cert = /etc/mysql/ssl/server-cert.pem
ssl_key = /etc/mysql/ssl/server-key.pem
```

```sql
ALTER USER 'app'@'10.0.%' REQUIRE SSL;
```

## 审计

- MySQL Enterprise Audit 或 MariaDB audit plugin
- 云 RDS 审计日志
- 至少记录：DDL、权限变更、失败登录

## 网络

```
应用子网 ──3306──► MySQL 安全组
                   ✗ 0.0.0.0/0
```

## 加固 checklist

- [ ] `local_infile = OFF`
- [ ] 删除匿名用户、test 库
- [ ] 密码策略：`validate_password` 组件
- [ ] 定期账号审计与轮转

安全基线不合规**不予上线**。
