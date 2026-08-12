---
title: MySQL 慢查询分析与 SQL 优化
date: 2026-08-14 11:15:00
tags:
  - MySQL
  - 慢查询
categories:
  - MySQL SRE
---

慢 SQL 是 MySQL 生产**最常见性能事故**来源。

## 开启慢日志

```ini
slow_query_log = ON
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 0.5
log_slow_admin_statements = ON
```

## pt-query-digest 分析

```bash
pt-query-digest /var/log/mysql/slow.log > report.txt
```

关注：Query time 总和、Examined rows、全表扫描。

## EXPLAIN 要点

```sql
EXPLAIN ANALYZE SELECT ...;
```

| type | 说明 |
|------|------|
| ALL | 全表扫描，需优化 |
| index | 全索引扫描 |
| range | 范围扫描，可接受 |
| ref/eq_ref | 较好 |
| const | 最优 |

## 常见优化

- 缺失索引 → 联合索引覆盖 WHERE + ORDER BY
- 深分页 → 延迟关联 / 游标分页
- 隐式类型转换 → 索引失效
- SELECT * → 只取必要列

## SRE 流程

1. 每周 Top 10 慢 SQL 推开发
2. 核心库变更 SQL 需 EXPLAIN 评审
3. 使用 `max_execution_time` 限制长查询（8.0）

## 工具

- PMM Query Analytics
- Percona Toolkit
- 云 RDS 性能洞察

慢查询治理是**持续过程**，不是一次性项目。
