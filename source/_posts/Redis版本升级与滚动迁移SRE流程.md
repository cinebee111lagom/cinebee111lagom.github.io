---
title: Redis 版本升级与滚动迁移 SRE 流程
date: 2026-08-13 18:00:00
tags:
  - Redis
  - 升级
categories:
  - Redis SRE
---

Redis 升级需兼顾**兼容性、停机窗口、回滚路径**。

## 升级路径

```
6.2 → 7.0 → 7.2（逐 minor 升级，阅读 Release Notes）
```

主从架构可**从库先行**：

1. 升级从库 1 → 等待 sync 正常
2. 依次升级其余从库
3. Sentinel 手动 failover 到最新从库
4. 升级旧主
5. 可选 failback

## Cluster 滚动升级

- 逐节点 `CLUSTER FAILOVER` / 停服升级
- 确保每步 slot 覆盖完整
- 使用 `redis-cli --cluster check` 验证

## 配置迁移

```bash
redis-cli CONFIG GET '*' > config-backup.txt
# 对比新版本 deprecated 参数
```

## 回滚

- 保留旧版二进制 + 旧 RDB
- 从库未升级前勿切主到新版

## 变更窗口

| 级别 | 窗口 | 审批 |
|------|------|------|
| Patch | 任意低峰 | SRE |
| Minor | 维护窗口 | SRE + 业务 |
| Major | 专用窗口 | 变更委员会 |

## Checklist

- [ ] Release Notes 无 breaking change 或已适配
- [ ]  staging 全量回归
- [ ] 备份完成
- [ ] 回滚脚本就绪
- [ ] 监控大盘值守

升级后 24h 加强观察 `slowlog`、`replication`、`memory`。
