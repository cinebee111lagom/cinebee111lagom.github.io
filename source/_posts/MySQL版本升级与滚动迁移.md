---
title: MySQL 版本升级与滚动迁移
date: 2026-08-14 12:15:00
tags:
  - MySQL
  - 升级
categories:
  - MySQL SRE
---

MySQL 升级需严格**兼容性验证 + 回滚路径**。

## 升级路径

```
5.7 → 8.0（EOL 5.7 务必迁移）
8.0.x → 8.0.y（小版本滚动）
```

## 主从滚动升级

1. 升级从库（停复制 → 升级 → 启动 → 追平）
2. 依次升级所有从库
3. Orchestrator 切换主到已升级从库
4. 升级旧主

## 8.0 注意事项

- 默认 `caching_sha2_password`
- 保留字、GROUP BY 行为变化
- `utf8` → 明确 `utf8mb4`

## 升级前

```bash
mysqlcheck -u root -p --all-databases
mysql_upgrade（8.0.16+ 已集成自动）
pt-upgrade 对比 staging
```

## 回滚

- 保留旧版二进制与全量备份
- 跨大版本回滚通常需逻辑恢复

## 变更窗口

| 类型 | 要求 |
|------|------|
| Patch | 低峰 + 通知 |
| Minor | 维护窗口 + 回归 |
| Major | 专项项目 + 灰度 |

升级后 48h 加强监控复制、慢查询、错误日志。
