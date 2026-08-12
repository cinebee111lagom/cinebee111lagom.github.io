---
title: Flink 生产安全配置
date: 2026-08-18 11:30:00
tags:
  - Flink
  - 安全
categories:
  - Flink SRE
---

Flink 生产需保护 REST API、数据传输与外部系统凭证。

## Kerberos（YARN/Hadoop 环境）

```yaml
security.kerberos.login.use-ticket-cache: false
security.kerberos.login.keytab: /etc/security/keytabs/flink.keytab
security.kerberos.login.principal: flink/_HOST@REALM
security.kerberos.krb5-conf.path: /etc/krb5.conf
```

## SSL 内部通信

```yaml
security.ssl.internal.enabled: true
security.ssl.internal.keystore: /etc/flink/keystore.jks
security.ssl.internal.keystore-password: xxx
security.ssl.internal.truststore: /etc/flink/truststore.jks
security.ssl.internal.truststore-password: xxx
```

## REST API 鉴权

```yaml
# 1.19+ 可配 Bearer Token / OAuth2（视发行版）
rest.flamegraph.enabled: false   # 生产关闭调试端点
web.upload.dir: /tmp/flink-uploads
```

- REST 8081 不对公网暴露
- 通过 Ingress + OAuth2 Proxy 或 VPN 访问

## 凭证管理

```yaml
# K8s Secret 注入
env:
  - name: AWS_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: flink-s3-creds
        key: access-key
```

- S3 Checkpoint 用 IAM Role（K8s IRSA）优于静态 Key
- JDBC 密码不进 jar，用 Secret/KMS

## 网络隔离

```
Flink TM/JM → 内网 VPC
  ├─ Kafka（SASL_SSL）
  ├─ S3/HDFS（Checkpoint）
  └─ MySQL/ES（Sink）
禁止 TM 访问公网（除必要对象存储 endpoint）
```

## 审计

- 作业提交日志（谁、何时、哪 jar）
- Savepoint 操作记录
- K8s Audit Log（Operator 变更）

## 检查清单

- [ ] REST 8081 内网 + 鉴权
- [ ] Kafka/MySQL 连接加密
- [ ] 无硬编码密码
- [ ] Checkpoint 桶私有 + 加密 at-rest
- [ ] 最小权限 IAM/ACL

安全与 **Kafka SRE、MySQL SRE** 系列配置对齐。
