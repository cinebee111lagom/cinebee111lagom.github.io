---
title: MySQL 临时表空间文件
date: 2026-09-08 05:45:00
tags:
  - MySQL
  - InnoDB
  - 临时表
  - DBA
categories:
  - MySQL
---

## 概述

MySQL 使用**临时表空间（Temporary Tablespace）**来存储用户创建的临时表以及优化器产生的内部临时表数据。

---

## 两类临时表空间

### 1. 共享临时表空间（ibtmp1）

这是 MySQL 5.7 引入的机制，替代了以前将临时表数据写入各自独立 `.ibd` 文件的方式。

```
# 文件位置（由参数控制）
innodb_temp_tablespaces_dir = ./#innodb_temp/
```

**核心特点：**

| 属性 | 说明 |
|---|---|
| 文件名 | `ibtmp1`（位于数据目录下） |
| 存储内容 | 用户临时表 + 内部临时表的回滚段 |
| 生命周期 | MySQL 启动时创建，关闭时销毁 |
| 是否可压缩 | 正常运行中不会自动收缩 |
| 最大大小 | 受 `innodb_temp_data_file_path` 限制，默认无限增长 |

### 2. 会话临时表空间（temp_ibt_XXX）

MySQL 8.0 引入，每个会话分配独立的临时表空间文件。

```
# 存放位置
#innodb_temp/temp_ibt_1   -- 会话1
#innodb_temp/temp_ibt_2   -- 会话2
...
```

存储会话临时表中的**回滚段数据**。

---

## 关键参数

```sql
-- 查看临时数据文件配置
SHOW VARIABLES LIKE 'innodb_temp_data_file_path';
-- 默认: ibtmp1:12M:autoextend

-- 查看临时表空间目录
SHOW VARIABLES LIKE 'innodb_temp_tablespaces_dir';

-- 限制单个临时表的最大空间（8.0+）
SET SESSION tmp_table_size = 67108864;       -- 64MB，内存临时表上限
SET GLOBAL max_heap_table_size = 67108864;

-- 内部临时表最大大小（磁盘临时表触发阈值）
SET SESSION tmp_table_size = 134217728;      -- 128MB
```

---

## ibtmp1 文件膨胀问题

这是最常见的运维痛点。

### 膨胀原因

```sql
-- 大查询产生的临时表未及时释放
-- 会话连接未正常断开
-- 排序、分组、DISTINCT、UNION 等操作产生大量内部临时表
```

### 诊断方法

```sql
-- 查看临时表空间当前大小
SELECT 
    FILE_NAME, 
    TABLESPACE_NAME,
    ROUND(TOTAL_EXTENTS * EXTENT_SIZE / 1024 / 1024, 2) AS size_mb,
    AUTOEXTENDED
FROM information_schema.FILES 
WHERE TABLESPACE_NAME = 'innodb_temporary';

-- 监控活跃的内部临时表使用
SELECT * FROM sys.memory_global_by_current_bytes 
WHERE EVENT_NAME LIKE '%temp%';
```

### 解决方案

**MySQL 8.0.23+：**

```sql
-- 直接限制 ibtmp1 最大为 2GB（可自定义）
-- my.cnf
[mysqld]
innodb_temp_data_file_path = ibtmp1:12M:autoextend:max:2G
```

**MySQL 5.7 / 旧版本重启收缩：**

```bash
# 唯一有效的收缩方式：重启 MySQL
systemctl stop mysqld
# 可选：删除旧的 ibtmp1（重启会自动重建）
rm /var/lib/mysql/ibtmp1
systemctl start mysqld
```

**MySQL 8.0.23+（动态调整）：**

```sql
-- 动态修改最大值，下次创建新文件时生效
ALTER INSTANCE RELOAD INNODB TEMP_DATA_FILE_PATH = 'ibtmp1:12M:autoextend:max:5G';
```

---

## 内存临时表 vs 磁盘临时表

理解何时数据会落到临时表空间：

```sql
-- 优化器决策流程：
-- 
-- 临时表数据量 < tmp_table_size / max_heap_table_size
--     → 使用 MEMORY 引擎（内存中，不涉及 ibtmp1）
--
-- 临时表数据量 > 阈值，或包含 BLOB/TEXT 列
--     → 转换为 InnoDB 磁盘临时表（写入 ibtmp1）

-- 查看是否发生了磁盘临时表
SHOW GLOBAL STATUS LIKE 'Created_tmp_disk_tables';
SHOW GLOBAL STATUS LIKE 'Created_tmp_tables';

-- MySQL 8.0 使用 TempTable 引擎（默认内存，溢出到磁盘）
SHOW VARIABLES LIKE 'internal_tmp_mem_storage_engine';  -- TempTable
SHOW VARIABLES LIKE 'temptable_max_ram';                 -- 默认1GB
```

---

## 架构总结

```
MySQL 8.0 临时表空间架构：

┌─────────────────────────────────────────┐
│              MySQL Server               │
│                                         │
│  会话A        会话B        会话N        │
│    │           │           │            │
│    ▼           ▼           ▼            │
│  ┌──────┐  ┌──────┐    ┌──────┐        │
│  │临时表 │  │临时表 │    │临时表 │        │
│  └──┬───┘  └──┬───┘    └──┬───┘        │
│     │         │           │             │
│     ▼         ▼           ▼             │
│  temp_ibt_1  temp_ibt_2  temp_ibt_N    │  ← 每会话回滚段
│                                         │
│         ┌──────────────┐                │
│         │    ibtmp1    │                │  ← 共享临时表数据
│         │ (共享临时表空间)│                │
│         └──────────────┘                │
└─────────────────────────────────────────┘
```

**关键区分：**
- **ibtmp1**：存储临时表的**数据页**
- **temp_ibt_XXX**：存储临时表的**回滚段**（用于事务回滚）
- 两者配合工作，MySQL 8.0 相比 5.7 做了显著的架构改进，避免了旧版本中 DDL 操作对共享临时表空间的争用

---

如果有具体场景（比如 ibtmp1 膨胀排查、临时表性能优化等），可以进一步展开。
