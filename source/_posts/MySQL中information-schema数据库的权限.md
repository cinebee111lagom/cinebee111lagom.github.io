---
title: MySQL中information_schema数据库的权限
date: 2026-09-08 02:15:00
tags:
  - MySQL
  - information_schema
  - 权限
  - DBA
categories:
  - MySQL
---

## 基本概念

`information_schema` 是 MySQL 内置的**虚拟数据库**，它不是一个真实的数据库，而是以**只读视图**的形式存在，提供服务器上所有数据库的元数据信息。

## 权限特点

### 1. 默认可访问性

- **任何拥有 MySQL 账号的用户**都可以查询 `information_schema`。
- 无需授予额外的权限即可访问。
- 查询结果会**根据当前用户的权限自动过滤**。

### 2. 核心机制

```
用户A 只有 db1 的权限 → 查询 information_schema 只能看到 db1 的表信息
用户B 有所有库的权限  → 查询 information_schema 能看到所有库的表信息
```

也就是说，**你能看到哪些信息，取决于你本身拥有哪些对象的权限**。

### 3. 只读性

- `information_schema` 是**只读**的，不能执行 `INSERT`、`UPDATE`、`DELETE`。
- 不能对其中的表执行 `DROP`、`ALTER` 等 DDL 操作。

### 4. 具体行为（按对象类型）

| 对象类型 | 权限要求 |
|---------|---------|
| `SCHEMATA`（数据库列表） | 只显示用户有任意权限的数据库 |
| `TABLES`（表信息） | 只显示用户能看到的表 |
| `COLUMNS`（列信息） | 只显示用户能看到的列 |
| `ROUTINES`（存储过程/函数） | 只显示用户有权查看的例程 |
| `TRIGGERS`、`VIEWS` 等 | 同理，按权限过滤 |

### 5. 特殊用户

- **`root` / 超级用户**：能看到所有信息。
- **`SELECT` 权限受限的用户**：只能看到自己被授权对象的元数据。

## 常见使用场景

```sql
-- 查看所有数据库
SELECT SCHEMA_NAME FROM information_schema.SCHEMATA;

-- 查看某库的所有表
SELECT TABLE_NAME 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'mydb';

-- 查看某表的列信息
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mydb' AND TABLE_NAME = 'users';

-- 查看表大小
SELECT TABLE_NAME, TABLE_ROWS, 
       ROUND(DATA_LENGTH/1024/1024, 2) AS data_mb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mydb'
ORDER BY DATA_LENGTH DESC;
```

## 注意事项

1. **`PROCESS` 权限**：拥有 `PROCESS` 权限的用户可以看到其他用户的线程/连接信息，这会影响 `information_schema.PROCESSLIST` 的查询结果。

2. **`information_schema_stats_expiry`**（MySQL 8.0+）：
   - 默认情况下 `TABLES` 和 `STATISTICS` 表的统计信息有缓存（默认 86400 秒）。
   - 可以通过设置为 `0` 实时获取最新数据：
   ```sql
   SET SESSION information_schema_stats_expiry = 0;
   ```

3. **性能影响**：在表非常多的情况下，查询 `information_schema` 可能较慢，因为它需要实时收集元数据（尤其是 MySQL 5.7 及更早版本中会触发表锁）。

## 一句话总结

> `information_schema` 对所有用户开放，但**所见即所权**——你能看到的信息范围严格受你自身权限的约束，且只能读、不能写。
