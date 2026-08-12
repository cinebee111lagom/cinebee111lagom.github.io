---
title: PostgreSQL 版本升级与滚动迁移
date: 2026-08-15 12:15:00
tags:
  - PostgreSQL
  - 升级
categories:
  - PostgreSQL SRE
---

PostgreSQL 大版本升级需谨慎，常用逻辑复制或 pg_upgrade 实现低停机迁移。

## 升级路径

| 方式 | 停机 | 适用 |
|------|------|------|
| pg_dump/pg_restore | 长 | 小库、跨大版本 |
| pg_upgrade | 短（分钟~小时） | 同机、大版本 |
| 逻辑复制 | 极短（切换） | 生产推荐 |
| 蓝绿 + Patroni | 可控 | HA 集群 |

## pg_upgrade 流程

```bash
# 1. 安装新版本二进制
# 2. initdb 新版本实例
/usr/pgsql-17/bin/pg_upgrade \
  --old-datadir=/var/lib/pgsql/16/data \
  --new-datadir=/var/lib/pgsql/17/data \
  --old-bindir=/usr/pgsql-16/bin \
  --new-bindir=/usr/pgsql-17/bin \
  --check

# 3. 停库 → 执行升级 → 启动新库
/usr/pgsql-17/bin/pg_upgrade ... 
./analyze.sh
./vacuumdb.sh --all --analyze-in-stages
```

## 逻辑复制升级（低停机）

```sql
-- 新版本库上
CREATE PUBLICATION mypub FOR ALL TABLES;

-- 旧版本库上
CREATE SUBSCRIPTION mysub
  CONNECTION 'host=newpg dbname=mydb user=repl password=xxx'
  PUBLICATION mypub;
```

同步完成后：
1. 停写旧库
2. 等待 subscription lag = 0
3. 切换 DNS/PgBouncer 到新库
4. 验证后下线旧库

## 小版本升级

```bash
# Patroni 滚动：先 standby 后 primary
patronictl restart pg-cluster pg2
patronictl restart pg-cluster pg1
```

## 升级前 Checklist

- [ ] 阅读 Release Notes（breaking changes）
- [ ] 扩展兼容性（PostGIS、pgvector）
- [ ] 全量备份 + PITR 可用
- [ ] staging 环境完整演练
- [ ] 应用 SQL 模式兼容性测试
- [ ] 回滚方案（保留旧库 N 天）

## 常见坑

- `pg_upgrade` 后必须 `analyze`
- 逻辑复制不支持 DDL 自动同步
- 大版本跳跃需逐级或使用 pg_dump

**原则**：先在 staging 跑通，生产选业务低峰 + 变更窗口。
