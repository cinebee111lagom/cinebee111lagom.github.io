---
title: Kafka 生产安全配置：SASL、SSL 与 ACL
date: 2026-08-16 11:30:00
tags:
  - Kafka
  - 安全
categories:
  - Kafka SRE
---

Kafka 生产环境必须启用认证、加密与 ACL，禁止 PLAINTEXT 裸奔。

## 监听器配置

```properties
listeners=SASL_SSL://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
advertised.listeners=SASL_SSL://10.0.1.11:9092
security.inter.broker.protocol=SASL_SSL
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512
sasl.enabled.mechanisms=SCRAM-SHA-512
ssl.keystore.location=/etc/kafka/secrets/kafka.keystore.jks
ssl.keystore.password=xxx
ssl.truststore.location=/etc/kafka/secrets/kafka.truststore.jks
ssl.truststore.password=xxx
ssl.client.auth=required
```

## 创建 SCRAM 用户

```bash
kafka-configs.sh --bootstrap-server localhost:9092 \
  --alter --add-config 'SCRAM-SHA-512=[password=secret]' \
  --entity-type users --entity-name app-producer
```

## ACL 示例

```bash
# Producer 写
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add --allow-principal User:app-producer \
  --operation Write --topic orders

# Consumer 读
kafka-acls.sh --bootstrap-server localhost:9092 \
  --add --allow-principal User:app-consumer \
  --operation Read --topic orders --group order-group

# 禁止 Wildcard 过大权限
```

## 授权器

```properties
authorizer.class.name=kafka.security.authorizer.AclAuthorizer
allow.everyone.if.no.acl.found=false
super.users=User:admin
```

## 网络隔离

```
Producer/Consumer VPC → SG → Kafka Broker（仅内网）
公网访问 → 通过 API Gateway / 专用 Proxy，非直连 Broker
```

## 审计

- Confluent Audit Logs / OpenSearch
- 记录 ACL 变更、认证失败
- 定期 review ACL 与 super.users

## 检查清单

- [ ] SASL_SSL 全链路（含 inter-broker）
- [ ] allow.everyone.if.no.acl.found=false
- [ ] 应用独立账号，最小权限
- [ ] 证书有效期监控
- [ ] 无 PLAINTEXT listener（生产）

安全基线纳入上线 Checklist，**与 Schema Registry、Connect 统一认证**。
