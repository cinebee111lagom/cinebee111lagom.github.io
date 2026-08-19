---
title: MySQL 索引失效原因全面解析
date: 2026-09-08 07:00:00
tags:
  - MySQL
  - 索引
  - 性能优化
  - SQL优化
categories:
  - MySQL
---

## 一、索引数据结构基础

在分析失效原因之前，先理解 B+Tree 索引的核心特性：

```
B+Tree 索引的有序性、最左前缀性、全值匹配性是判断是否走索引的根本依据。
```

---

## 二、联合索引相关失效

### 1. 违反最左前缀原则

```sql
-- 联合索引: idx(a, b, c)

-- ✅ 走索引
SELECT * FROM t WHERE a = 1;
SELECT * FROM t WHERE a = 1 AND b = 2;
SELECT * FROM t WHERE a = 1 AND b = 2 AND c = 3;

-- ❌ 不走索引（跳过了最左列 a）
SELECT * FROM t WHERE b = 2;
SELECT * FROM t WHERE b = 2 AND c = 3;
SELECT * FROM t WHERE c = 3;
```

**原理：** B+Tree 按 `(a, b, c)` 的顺序排序，没有 `a` 就无法定位搜索起点。

### 2. 联合索引中间列断开

```sql
-- 联合索引: idx(a, b, c)

-- ✅ 只用到 a（b 断开后 c 无法使用）
SELECT * FROM t WHERE a = 1 AND c = 3;

-- 跳过 b，索引只生效到 a 为止
```

### 3. 联合索引范围查询后的列失效

```sql
-- 联合索引: idx(a, b, c)

-- a 等值 → b 范围 → c 失效（MySQL 5.6 引入 Index Condition Pushdown 优化后有改善）
SELECT * FROM t WHERE a = 1 AND b > 10 AND c = 3;
--   a: ✅ 索引生效
--   b: ✅ 索引生效（范围）
--   c: ❌ 索引不生效（范围后的列无法有序）
```

**原理：** 范围查询破坏了后续列的有序性，B+Tree 无法利用 `c` 进行有序查找。

---

## 三、查询条件导致失效

### 4. 在索引列上使用函数或表达式

```sql
-- ❌ 对索引列使用函数
SELECT * FROM t WHERE LEFT(name, 3) = 'Tom';
SELECT * FROM t WHERE YEAR(create_time) = 2024;
SELECT * FROM t WHERE id + 1 = 10;

-- ✅ 改写为（函数作用于常量，列保持原始形式）
SELECT * FROM t WHERE name LIKE 'Tom%';
SELECT * FROM t WHERE create_time >= '2024-01-01'
                   AND create_time < '2025-01-01';
SELECT * FROM t WHERE id = 9;
```

**原理：** 函数/表达式破坏了索引列的原始值，B+Tree 中存储的是原始值，无法匹配。

### 5. 隐式类型转换

```sql
-- phone 列是 VARCHAR 类型，索引 idx_phone(phone)

-- ❌ 传入数字，MySQL 会隐式将 VARCHAR 转为数字比较
SELECT * FROM t WHERE phone = 13800138000;
-- 等价于: WHERE CAST(phone AS DECIMAL) = 13800138000 → 索引失效

-- ✅ 传入字符串，类型匹配
SELECT * FROM t WHERE phone = '13800138000';
```

> **注意：** 字符串列传数字会触发类型转换导致索引失效；反过来，数字列传字符串，MySQL 会将字符串转数字，索引仍然生效。

### 6. 隐式字符集转换

```sql
-- 两个表字符集不同（utf8 vs utf8mb4），关联查询时会触发隐式转换
-- t1.utf8_col = t2.utf8mb4_col → 索引失效
```

### 7. 对索引列使用 `LIKE` 左模糊

```sql
-- name 上有索引

-- ❌ 左模糊，无法利用索引的有序性
SELECT * FROM t WHERE name LIKE '%Tom';

-- ❌ 双百分号
SELECT * FROM t WHERE name LIKE '%Tom%';

-- ✅ 右模糊可以走索引
SELECT * FROM t WHERE name LIKE 'Tom%';
```

### 8. `OR` 条件中有无索引列

```sql
-- name 有索引，age 无索引

-- ❌ 整个条件不走索引（MySQL 认为全表扫描更优）
SELECT * FROM t WHERE name = 'Tom' OR age = 25;

-- ✅ 改写为 UNION
SELECT * FROM t WHERE name = 'Tom'
UNION
SELECT * FROM t WHERE age = 25;
```

### 9. `NOT` / `!=` / `<>` / `NOT IN`

```sql
-- ❌ 不等于条件通常不走索引（优化器认为全表扫描更划算）
SELECT * FROM t WHERE status != 1;
SELECT * FROM t WHERE status <> 1;
SELECT * FROM t WHERE name NOT IN ('Tom', 'Jerry');

-- 但不是绝对的，如果数据分布特殊（如 99% 都是 0，查 != 0）可能走索引
```

### 10. `IS NULL` / `IS NOT NULL`

```sql
-- 是否走索引取决于数据分布和优化器判断
-- 在较新版本的 MySQL 中，NULL 值也会存储在 B+Tree 中，可以走索引
-- 但数据量大且大部分为 NULL 时，优化器可能选择全表扫描
```

---

## 四、优化器决策相关

### 11. 优化器认为全表扫描更快

```sql
-- 即使有索引，当查询需要回表的数据量超过一定比例时
-- MySQL 优化器会选择全表扫描（约 20%~30% 的数据）

SELECT * FROM t WHERE status = 1;  -- 如果 80% 的数据 status=1
-- 优化器判断: 全表扫描成本 < 索引查找 + 大量回表 成本
```

### 12. 统计信息不准确

```sql
-- 表数据变化频繁但统计信息未更新
ANALYZE TABLE t;  -- 手动更新统计信息

-- InnoDB 通过采样估算，可能存在偏差导致优化器误判
```

### 13. 使用 `SELECT *`

```sql
-- 回表成本高时，优化器放弃索引
SELECT * FROM t WHERE name = 'Tom';

-- ✅ 覆盖索引：只查索引包含的列，无需回表
SELECT name, age FROM t WHERE name = 'Tom';
-- (name, age) 上有联合索引时，直接在索引中完成查询
```

---

## 五、其他常见场景

### 14. 索引列参与计算

```sql
-- ❌
SELECT * FROM t WHERE YEAR(date_col) = 2024;

-- ✅ 改写为范围查询
SELECT * FROM t WHERE date_col >= '2024-01-01'
                   AND date_col < '2025-01-01';
```

### 15. 使用 `ORDER BY` 不当

```sql
-- 联合索引 idx(a, b, c)

-- ❌ 排序方向不一致（MySQL 8.0 之前）
SELECT * FROM t WHERE a = 1 ORDER BY b ASC, c DESC;

-- ✅ MySQL 8.0+ 支持降序索引
CREATE INDEX idx ON t(a, b ASC, c DESC);

-- ❌ ORDER BY 字段不满足最左前缀
SELECT * FROM t WHERE a = 1 ORDER BY c;  -- 跳过了 b
```

### 16. `GROUP BY` 不当

```sql
-- 与 ORDER BY 类似，需要满足最左前缀原则
-- ❌
SELECT a, c, COUNT(*) FROM t GROUP BY a, c;  -- 跳过了 b
```

### 17. 使用 `IN` 子查询

```sql
-- ❌ 子查询可能不走索引
SELECT * FROM t1 WHERE id IN (SELECT id FROM t2 WHERE status = 1);

-- ✅ 改用 EXISTS 或 JOIN
SELECT t1.* FROM t1
INNER JOIN t2 ON t1.id = t2.id
WHERE t2.status = 1;

-- MySQL 8.0+ 对 IN 子查询做了半连接优化，可能已经自动优化
```

### 18. 使用 `LIMIT` 大偏移

```sql
-- 大 offset 效率低，虽然可能走索引但性能差
SELECT * FROM t ORDER BY id LIMIT 1000000, 10;

-- ✅ 延迟关联
SELECT * FROM t
INNER JOIN (SELECT id FROM t ORDER BY id LIMIT 1000000, 10) tmp
ON t.id = tmp.id;
```

---

## 六、速查总结表

| 序号 | 失效场景 | 解决方案 |
|:---:|---|---|
| 1 | 违反最左前缀 | 调整查询条件顺序或补充索引 |
| 2 | 联合索引中间列断开 | 查询条件覆盖完整前缀 |
| 3 | 范围查询后的列 | 调整索引列顺序，等值列在前 |
| 4 | 索引列使用函数 | 将函数移到常量侧或使用生成列 |
| 5 | 隐式类型转换 | 保证查询值类型与列类型一致 |
| 6 | 隐式字符集转换 | 统一表和列的字符集 |
| 7 | `LIKE` 左模糊 | 改为右模糊或使用全文索引 |
| 8 | `OR` 含无索引列 | 用 `UNION` 拆分或补建索引 |
| 9 | `!=` / `NOT IN` | 改写为 `UNION` 或接受全表扫描 |
| 10 | `IS NULL / NOT NULL` | 评估数据分布，必要时强制索引 |
| 11 | 优化器选择全表扫描 | 减少回表，使用覆盖索引 |
| 12 | 统计信息过期 | `ANALYZE TABLE` 更新统计信息 |
| 13 | `SELECT *` 回表代价高 | 只选必要列，利用覆盖索引 |
| 14 | 索引列参与计算 | 改写为范围查询 |
| 15 | `ORDER BY` 不当 | 遵循最左前缀，注意排序方向 |
| 16 | 子查询效率低 | 改为 `JOIN` 或 `EXISTS` |

---

## 七、排查工具

```sql
-- 1. EXPLAIN 查看执行计划
EXPLAIN SELECT * FROM t WHERE a = 1;

-- 重点关注：
--   type: ALL(全表) > index > range > ref > eq_ref > const
--   key: NULL 表示没走索引
--   rows: 扫描行数
--   Extra: Using filesort / Using temporary 表示需优化

-- 2. EXPLAIN ANALYZE（MySQL 8.0.18+）
EXPLAIN ANALYZE SELECT * FROM t WHERE a = 1;
-- 输出实际执行时间，更精确

-- 3. SHOW PROFILE
SET profiling = 1;
SELECT * FROM t WHERE a = 1;
SHOW PROFILES;

-- 4. 慢查询日志
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;  -- 超过1秒记录
```

> **核心原则：** 索引的本质是 B+Tree 的有序查找，任何破坏索引列**原始值**、**有序性**、**最左前缀**的操作都可能导致索引失效。写 SQL 时始终思考：**优化器能否利用索引的有序性来减少扫描范围？**
