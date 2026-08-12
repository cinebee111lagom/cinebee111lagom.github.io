---
title: Redis 连接池与客户端部署最佳实践
date: 2026-08-13 17:30:00
tags:
  - Redis
  - 客户端
categories:
  - Redis SRE
---

应用侧连接管理不当会导致 **连接耗尽、TIME_WAIT 爆炸**，SRE 需制定客户端规范。

## 连接数规划

```conf
# redis.conf
maxclients 10000
```

```
总连接 ≈ Σ(应用 Pod 数 × 每 Pod 连接池 maxTotal)
```

预留 30% 余量，监控 `connected_clients`。

## 连接池配置（Java Lettuce 示例）

```yaml
spring.redis.lettuce.pool:
  max-active: 32
  max-idle: 16
  min-idle: 4
  max-wait: 3000ms
```

| 参数 | 建议 |
|------|------|
| max-active | 按 QPS 与 RT 估算，避免过大 |
| min-idle | 保持热连接，减少握手 |
| timeout | 3~5s，防雪崩 |

## 常见错误

- ❌ 每请求 new 连接不关闭
- ❌ 连接池 max 过大（1000+ / 进程）
- ❌ 无 timeout，阻塞拖死线程池
- ❌ 直连单 IP 非 Sentinel/Cluster 客户端

## Sentinel / Cluster 客户端

- 必须支持拓扑自动发现
- 故障转移后自动切新主

## 部署规范

- 应用与 Redis 同 AZ，降低 RT
- TLS 连接注意握手开销，适当增大池
- 发布前压测验证连接数峰值

连接池配置写入**应用上线 checklist**，与 Redis 侧 maxclients 联动评审。
