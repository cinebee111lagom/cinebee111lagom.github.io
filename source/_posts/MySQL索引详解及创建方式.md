---
title: MySQL 索引详解及创建方式
date: 2026-09-08 06:45:00
tags:
  - MySQL
  - 索引
  - InnoDB
  - 性能优化
categories:
  - MySQL
---

## 一、什么是索引？

索引是一种**数据结构**，类似于书籍的目录。它帮助数据库引擎快速定位到需要的数据行，避免全表扫描，从而大幅提升查询效率。

**核心原理：** 索引将表中的一列或多列值按照特定数据结构（如 B+ 树）进行排序存储，并在这些值与对应的数据行之间建立映射关系。

---

## 二、索引的类型

| 类型 | 说明 |
|------|------|
| **主键索引 (PRIMARY KEY)** | 唯一且不允许为 NULL，每张表只能有一个 |
| **唯一索引 (UNIQUE)** | 列值必须唯一，允许为 NULL |
| **普通索引 (INDEX)** | 最基本的索引，无唯一性限制 |
| **全文索引 (FULLTEXT)** | 用于全文检索，适合大文本字段 |
| **组合索引 (Composite)** | 在多列上建立的索引 |
| **空间索引 (SPATIAL)** | 用于地理空间数据类型 |

---

## 三、索引的数据结构

### 1. B+ 树索引（最常用）

```
              [30 | 60]
             /    |    \
      [10|20] [40|50] [70|80]
       / | \   / | \   / | \
     叶子节点之间通过链表相连 → 范围查询高效
```

**特点：**
- 非叶子节点只存储键值，叶子节点存储数据
- 叶子节点通过双向链表连接，支持范围查询
- 树的高度通常为 3~4 层，亿级数据也只需 3~4 次磁盘 IO

### 2. Hash 索引

- 基于哈希表，等值查询 O(1)
- **不支持范围查询**和排序
- Memory 引擎默认支持，InnoDB 自适应哈希索引

### 3. 全文索引

- 倒排索引结构，适合文本搜索
- MySQL 5.6+ InnoDB 开始支持

---

## 四、创建索引的方式

### 1. 建表时创建

```sql
CREATE TABLE user (
    id        BIGINT       NOT NULL AUTO_INCREMENT,
    username  VARCHAR(50)  NOT NULL,
    email     VARCHAR(100) NOT NULL,
    age       INT          DEFAULT NULL,
    bio       TEXT,
    created_at DATETIME    DEFAULT CURRENT_TIMESTAMP,

    -- 主键索引
    PRIMARY KEY (id),

    -- 唯一索引
    UNIQUE INDEX uk_email (email),

    -- 普通索引
    INDEX idx_username (username),

    -- 组合索引
    INDEX idx_username_age (username, age),

    -- 全文索引
    FULLTEXT INDEX ft_bio (bio)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2. 对已有表添加索引

```sql
-- 普通索引
CREATE INDEX idx_username ON user(username);

-- 唯一索引
CREATE UNIQUE INDEX uk_email ON user(email);

-- 组合索引
CREATE INDEX idx_name_age ON user(username, age);

-- 全文索引
CREATE FULLTEXT INDEX ft_bio ON user(bio);
```

### 3. ALTER TABLE 方式

```sql
-- 添加普通索引
ALTER TABLE user ADD INDEX idx_username (username);

-- 添加唯一索引
ALTER TABLE user ADD UNIQUE INDEX uk_email (email);

-- 添加组合索引
ALTER TABLE user ADD INDEX idx_name_age (username, age);

-- 添加主键（前提是没有主键）
ALTER TABLE user ADD PRIMARY KEY (id);
```

### 4. 删除索引

```sql
-- 删除普通/唯一/全文索引
DROP INDEX idx_username ON user;

-- 删除主键索引
ALTER TABLE user DROP PRIMARY KEY;

-- ALTER 方式删除
ALTER TABLE user DROP INDEX idx_name_age;
```

### 5. 查看索引

```sql
-- 查看表的所有索引
SHOW INDEX FROM user;

-- 或者
SHOW KEYS FROM user;
```

---

## 五、组合索引与最左前缀原则

这是面试和实际开发中**最重要的概念之一**。

```sql
CREATE INDEX idx_abc ON table_name (col_a, col_b, col_c);
```

该索引相当于同时创建了：

| 等效索引 | 可使用的查询 |
|----------|-------------|
| `(col_a)` | `WHERE col_a = ?` |
| `(col_a, col_b)` | `WHERE col_a = ? AND col_b = ?` |
| `(col_a, col_b, col_c)` | `WHERE col_a = ? AND col_b = ? AND col_c = ?` |

**最左前缀原则：** 查询条件必须从索引的最左列开始，且不跳过中间列，索引才能生效。

```sql
-- ✅ 能命中索引
SELECT * FROM t WHERE col_a = 1;
SELECT * FROM t WHERE col_a = 1 AND col_b = 2;
SELECT * FROM t WHERE col_a = 1 AND col_b = 2 AND col_c = 3;

-- ❌ 无法命中索引（跳过了 col_a）
SELECT * FROM t WHERE col_b = 2;
SELECT * FROM t WHERE col_b = 2 AND col_c = 3;

-- ⚠️ 部分命中（只用到 col_a，col_c 无法利用索引）
SELECT * FROM t WHERE col_a = 1 AND col_c = 3;
```

---

## 六、索引失效的常见场景

```sql
-- 1. 对索引列使用函数
SELECT * FROM user WHERE LEFT(username, 3) = 'zhang';  -- ❌ 失效
SELECT * FROM user WHERE username LIKE 'zhang%';       -- ✅ 走索引

-- 2. 隐式类型转换
-- phone 是 VARCHAR 类型
SELECT * FROM user WHERE phone = 13800138000;   -- ❌ 数字导致隐式转换
SELECT * FROM user WHERE phone = '13800138000'; -- ✅

-- 3. LIKE 以通配符开头
SELECT * FROM user WHERE username LIKE '%zhang%';  -- ❌ 失效
SELECT * FROM user WHERE username LIKE 'zhang%';   -- ✅ 走索引

-- 4. OR 连接非索引列
SELECT * FROM user WHERE username = 'zhang' OR age = 25;
-- 如果 age 无索引，则整体不走索引

-- 5. 使用 != 或 NOT IN
SELECT * FROM user WHERE username != 'zhang';  -- ⚠️ 可能失效

-- 6. IS NULL / IS NOT NULL（视数据分布而定）
```

---

## 七、EXPLAIN 执行计划分析

```sql
EXPLAIN SELECT * FROM user WHERE username = 'zhangsan';
```

关键字段说明：

| 字段 | 说明 |
|------|------|
| **type** | 访问类型，从好到差：`system > const > eq_ref > ref > range > index > ALL` |
| **key** | 实际使用的索引名称，NULL 表示没走索引 |
| **rows** | 预估扫描行数，越小越好 |
| **Extra** | 额外信息：`Using index`（覆盖索引）、`Using filesort`（文件排序，需优化） |

---

## 八、索引设计最佳实践

### 1. 选择合适的列建索引

```
✅ WHERE 子句中频繁出现的列
✅ JOIN 连接的列
✅ ORDER BY / GROUP BY 的列
✅ 高选择性（区分度高）的列

❌ 数据量小的表不需要索引
❌ 频繁更新的列谨慎建索引（写入性能下降）
❌ 重复值过多的列（如性别字段）不建议单独建索引
```

### 2. 覆盖索引优化

```sql
-- 组合索引 idx_name_age (username, age)

-- 查询只需要索引中的列，无需回表
SELECT username, age FROM user WHERE username = 'zhang';
-- EXPLAIN 中 Extra 显示 Using index ✅
```

### 3. 前缀索引（减少索引体积）

```sql
-- 对长字符串只取前 N 个字符
CREATE INDEX idx_email_prefix ON user(email(10));

-- 选择合适的前缀长度
SELECT
    COUNT(DISTINCT LEFT(email, 5))  / COUNT(*) AS sel5,
    COUNT(DISTINCT LEFT(email, 10)) / COUNT(*) AS sel10,
    COUNT(DISTINCT LEFT(email, 15)) / COUNT(*) AS sel15,
    COUNT(DISTINCT email)           / COUNT(*) AS sel_full
FROM user;
```

---

## 九、InnoDB 聚簇索引 vs 非聚簇索引

```
┌─────────────────────────────────────────────────┐
│              聚簇索引 (主键索引)                   │
│                                                   │
│   B+ 树叶子节点直接存储完整的行数据                  │
│   每张表只能有一个                                  │
│   InnoDB 主键索引就是聚簇索引                       │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│            非聚簇索引 (二级索引/辅助索引)           │
│                                                   │
│   B+ 树叶子节点存储的是主键值                        │
│   查询需要「回表」：先查二级索引拿到主键，             │
│   再通过主键去聚簇索引中查找完整数据                   │
└─────────────────────────────────────────────────┘
```

**查询流程示例：**

```sql
-- 表有主键索引 (id) 和二级索引 idx_name (username)
SELECT * FROM user WHERE username = 'zhangsan';

-- 第1步：在 idx_name 的 B+ 树中找到 username='zhangsan' → 得到 id=100
-- 第2步：在主键索引的 B+ 树中用 id=100 回表 → 拿到完整行数据
```

---

## 十、总结速查

```
索引创建三问：
1. 在哪些列上建？ → 高频查询、高区分度、JOIN/ORDER BY 的列
2. 建什么类型？   → 一般用 B+ 树索引（默认），全文搜索用 FULLTEXT
3. 单列还是组合？ → 多条件查询优先考虑组合索引，注意最左前缀

索引是空间换时间的典型手段：
✅ 大幅提升 SELECT 查询速度
❌ 占用额外磁盘空间
❌ 降低 INSERT/UPDATE/DELETE 的写入速度
```

合理设计索引是数据库性能优化中**性价比最高**的手段。建议在开发中养成使用 `EXPLAIN` 分析慢查询的习惯，逐步优化索引策略。
