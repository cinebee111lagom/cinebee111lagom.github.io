---
title: Kafka 版本升级与滚动迁移
date: 2026-08-16 12:00:00
tags:
  - Kafka
  - 升级
categories:
  - Kafka SRE
---

Kafka 升级需遵循 **Broker → 客户端** 顺序，滚动重启保证可用性。

## 升级路径

| 方式 | 停机 | 适用 |
|------|------|------|
| 滚动升级 | 无（分区短暂迁移） | 小版本、同大版本 |
| 双集群 + MM2 | 切换窗口 | 大版本跳跃 |
| KRaft 迁移 | 计划窗口 | ZK → KRaft |

## 滚动升级步骤

```bash
# 1. 确认 inter.broker.protocol 与 log.message.format 兼容
# 2. 逐 Broker 滚动：
systemctl stop kafka
# 替换二进制 / 更新 Docker 镜像
systemctl start kafka

# 3. 验证 ISR 恢复
kafka-topics.sh --describe --under-replicated-partitions \
  --bootstrap-server localhost:9092
```

## 协议版本

```properties
inter.broker.protocol.version=3.6-IV2
log.message.format.version=3.6-IV2
```

**先升级 Broker 二进制，再逐步 bump protocol version**（全集群升级完成后统一提）。

## ZK → KRaft 迁移

1. 部署新 KRaft 集群（staging）
2. MirrorMaker 2 双写或切换
3. 客户端切 bootstrap
4. 下线 ZK 集群

使用官方 `kafka-kraft.sh` 迁移工具，**生产前完整演练**。

## 升级前 Checklist

- [ ] 阅读 Release Notes（KIP breaking changes）
- [ ] 全集群 URP = 0
- [ ] 客户端兼容性矩阵
- [ ] 备份 / MM2 就绪
- [ ] staging 完整升级 + 压测
- [ ] 回滚方案（保留旧二进制）

## 常见坑

- 跨 2+ 大版本需逐级升级
- 升级中 Controller 切换可能短暂
- `log.message.format` 不可逆降级

**原则**：低峰滚动、一次一个 Broker、ISR 恢复后再下一个。
