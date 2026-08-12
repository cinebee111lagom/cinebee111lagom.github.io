---
title: Redis 大 Key 与热 Key 治理
date: 2026-08-13 17:45:00
tags:
  - Redis
  - 大Key
categories:
  - Redis SRE
---

大 Key 阻塞单线程，热 Key 打爆单分片——Cluster 也扛不住。

## 大 Key 定义（经验值）

| 类型 | 阈值 |
|------|------|
| String | value > 10KB（警惕），> 1MB（必须拆） |
| Hash/List/Set/ZSet | 元素 > 5000 |
| 单 Key 内存 | > 10MB |

## 扫描工具

```bash
redis-cli --bigkeys -h host -a pass
redis-cli --memkeys -h host -a pass   # Redis 4+
```

生产用 `SCAN` 离线脚本，避免 `--bigkeys` 高峰跑。

## 大 Key 处理

- String 拆分为多个 chunk
- Hash 按 field 范围分 key
- 异步删除：`UNLINK` 替代 `DEL`（Redis 4+）

## 热 Key

**现象**：单 key QPS 极高，Cluster 单 slot 过热。

**方案**：

1. **本地缓存**（Caffeine）挡一层
2. **热 key 副本**：读随机分散到 `{tag}:key:1` ~ `{tag}:key:N`
3. **读写分离**：从库分担读（注意复制延迟）

## 监控

- 导出 top key 内存（redis_exporter 扩展）
- 业务侧埋点 hot key 访问频率

## SRE 流程

- 上线前 Code Review 禁止大 value 入 Redis
- 每月 bigkeys 扫描报告
- 热 key 告警 → 协调开发加本地缓存

大 Key / 热 Key 是 Redis **性能事故**头号元凶。
