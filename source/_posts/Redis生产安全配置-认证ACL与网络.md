---
title: Redis 生产安全配置：认证、ACL 与网络
date: 2026-08-13 15:45:00
tags:
  - Redis
  - 安全
categories:
  - Redis SRE
---

Redis 默认无认证、绑定所有接口——**生产必须加固**。

## 基础加固

```conf
bind 10.0.1.10          # 仅内网 IP
protected-mode yes
requirepass strong_password_here
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command CONFIG "CONFIG_a8f3b2"
```

## ACL（Redis 6+）

```bash
ACL SETUSER appuser on >app_pass ~cache:* +get +set +del +expire
ACL SETUSER readonly on >ro_pass ~* +@read
ACL LIST
```

按应用最小权限：读写分离账号、禁止 DEBUG/CONFIG。

## 网络隔离

```
应用 VPC ──6379──► Redis 安全组（仅应用子网）
                    ✗ 公网
                    ✗ 0.0.0.0/0
```

K8s 使用 NetworkPolicy 限制仅业务 Pod 访问 Redis Service。

## TLS 加密

```conf
tls-port 6379
port 0
tls-cert-file /etc/redis/tls/redis.crt
tls-key-file /etc/redis/tls/redis.key
tls-ca-cert-file /etc/redis/tls/ca.crt
```

云托管通常默认 TLS；自建需证书轮换流程。

## 审计

- 开启慢日志 + 命令审计（ACL log）
- 定期扫描未授权访问、弱密码
- 禁止把 Redis 暴露到公网（历史高危漏洞多）

安全基线纳入**上线 checklist**，缺一项不予投产。
