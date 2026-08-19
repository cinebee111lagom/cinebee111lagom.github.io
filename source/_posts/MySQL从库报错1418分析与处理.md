---
title: MySQL 从库报错1418分析与处理
date: 2026-09-08 06:00:00
tags:
  - MySQL
  - 主从复制
  - 故障排查
  - DBA
categories:
  - MySQL
---

## 错误描述

错误 1418 完整信息：

```
ERROR 1418 (HY000): This function has none of DETERMINISTIC, NO SQL, or READS SQL DATA in its declaration and binary logging is enabled (you *might* want to use the less safe log_bin_trust_function_creators variable)
```

---

## 错误原因

在主从复制环境下，MySQL 为了保证**数据一致性**，对存储函数/过程有严格的安全检查。

**核心问题：**
- 创建函数时没有声明函数特性（是否确定性、是否读写数据等）
- 开启 binlog 后，MySQL 无法判断函数行为是否会导致主从数据不一致

**触发场景：**
- 从库回放包含创建函数/调用函数的 binlog 事件
- 主库创建的函数缺少特性声明，从库回放时报错
- 直接在从库上执行创建函数操作

---

## 函数特性说明

| 特性 | 含义 |
|------|------|
| `DETERMINISTIC` | 相同输入总是产生相同输出（如数学计算） |
| `NOT DETERMINISTIC` | 可能产生不同结果（如依赖时间、随机数） |
| `NO SQL` | 函数不包含任何 SQL 语句 |
| `READS SQL DATA` | 函数只读取数据，不修改 |
| `MODIFIES SQL DATA` | 函数会修改数据（INSERT/UPDATE/DELETE） |
| `CONTAINS SQL` | 函数包含 SQL 语句（默认值） |

---

## 解决方案

### 方案一：声明函数特性（推荐）

创建函数时明确声明特性，这是最规范的做法：

```sql
-- 示例：确定性函数
DELIMITER //
CREATE FUNCTION my_calc(x INT) 
RETURNS INT
DETERMINISTIC          -- 声明为确定性函数
READS SQL DATA         -- 声明只读数据
BEGIN
    RETURN x * 2;
END //
DELIMITER ;
```

```sql
-- 示例：不包含 SQL 的函数
DELIMITER //
CREATE FUNCTION my_format(str VARCHAR(100))
RETURNS VARCHAR(100)
DETERMINISTIC
NO SQL                 -- 声明不包含 SQL
BEGIN
    RETURN TRIM(UPPER(str));
END //
DELIMITER ;
```

---

### 方案二：设置全局参数（快速修复）

```sql
-- 在主库和从库都执行
SET GLOBAL log_bin_trust_function_creators = 1;
```

使其永久生效，修改配置文件：

```ini
# my.cnf 或 my.ini
[mysqld]
log_bin_trust_function_creators = 1
```

修改后重启 MySQL 或动态生效。

**参数说明：**
| 值 | 含义 |
|---|---|
| `0`（默认） | 严格模式，函数必须声明特性 |
| `1` | 信任模式，允许创建未声明特性的函数 |

---

### 方案三：主从同时修改 SQL 模式

如果问题与 SQL 模式相关：

```sql
-- 查看当前 SQL 模式
SELECT @@sql_mode;

-- 移除相关严格模式（如果存在）
SET GLOBAL sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
```

---

## 排查流程

```
报错 1418
    │
    ├─ 检查当前 log_bin_trust_function_creators 值
    │      │
    │      ├─ 值为 0 → 考虑修改为 1 或重新创建函数
    │      └─ 值为 1 → 检查其他配置问题
    │
    ├─ 检查触发报错的函数定义
    │      │
    │      ├─ 是否缺少特性声明 → 补充声明
    │      └─ 是否含有不确定性逻辑 → 标记为 NOT DETERMINISTIC
    │
    └─ 检查主从是否配置一致
           │
           ├─ binlog_format 是否相同
           └─ sql_mode 是否相同
```

---

## 推荐做法

**生产环境建议：**

```sql
-- 1. 先查看当前配置
SHOW VARIABLES LIKE 'log_bin_trust_function_creators';

-- 2. 创建函数时规范声明
DELIMITER //
CREATE FUNCTION calculate_score(input_val INT)
RETURNS DECIMAL(10,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE result DECIMAL(10,2);
    SELECT some_column INTO result FROM some_table WHERE id = input_val;
    RETURN result;
END //
DELIMITER ;

-- 3. 主从配置保持一致
```

---

## 注意事项

1. **不推荐在生产环境长期使用** `log_bin_trust_function_creators = 1`，会降低数据一致性保障

2. **主从配置一致性**：主库和从库的 `log_bin_trust_function_creators` 值应保持一致

3. **函数安全声明**：养成创建函数时声明特性的习惯，避免后续主从复制问题

4. **测试验证**：修改配置后，先在测试环境验证函数能否正常创建和调用
