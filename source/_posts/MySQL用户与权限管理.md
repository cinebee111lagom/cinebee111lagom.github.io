---
title: MySQL 用户与权限管理
date: 2026-09-08 02:45:00
tags:
  - MySQL
  - 权限
  - 用户管理
  - DBA
categories:
  - MySQL
---

## 一、用户管理

### 1. 创建用户

```sql
-- 基本语法
CREATE USER 'username'@'host' IDENTIFIED BY 'password';

-- 示例：允许本地登录
CREATE USER 'dev'@'localhost' IDENTIFIED BY 'MyPass123!';

-- 示例：允许任意主机登录（生产环境慎用）
CREATE USER 'dev'@'%' IDENTIFIED BY 'MyPass123!';

-- 示例：允许特定网段
CREATE USER 'dev'@'192.168.1.%' IDENTIFIED BY 'MyPass123!';
```



### 2. 查看用户

```sql
-- 查看所有用户
SELECT user, host, authentication_string FROM mysql.user;

-- 查看当前用户
SELECT CURRENT_USER();
SELECT USER();
```

### 3. 修改用户

```sql
-- 修改密码（MySQL 5.7+）
ALTER USER 'dev'@'localhost' IDENTIFIED BY 'NewPass456!';

-- 修改密码（MySQL 5.6 及以下）
SET PASSWORD FOR 'dev'@'localhost' = PASSWORD('NewPass456!');

-- 重命名用户
RENAME USER 'dev'@'localhost' TO 'developer'@'localhost';
```

### 4. 删除用户

```sql
DROP USER 'dev'@'localhost';

-- 注意：删除用户会自动撤销其所有权限
```

---

## 二、权限体系总览



### MySQL 权限层级

```
全局权限 (Global)          → *.*        影响整个服务器
├── 数据库权限 (Database)  → db_name.*  影响某个数据库
│   ├── 表权限 (Table)     → db.table   影响某张表
│   │   ├── 列权限 (Column)→ db.col     影响某一列
│   │   └── ...
│   └── ...
└── 存储过程权限 (Routine)  → 影响存储过程/函数
```

### 常见权限列表

| 权限 | 说明 | 作用范围 |
|---|---|---|
| `ALL PRIVILEGES` | 所有权限 | 全局/库/表 |
| `SELECT` | 查询数据 | 表/列 |
| `INSERT` | 插入数据 | 表/列 |
| `UPDATE` | 更新数据 | 表/列 |
| `DELETE` | 删除数据 | 表 |
| `CREATE` | 创建数据库/表 | 全局/库/表 |
| `DROP` | 删除数据库/表 | 全局/库/表 |
| `ALTER` | 修改表结构 | 全局/库/表 |
| `INDEX` | 创建/删除索引 | 全局/库/表 |
| `GRANT OPTION` | 允许授予自身拥有的权限 | 全局/库/表 |
| `PROCESS` | 查看所有线程 | 全局 |
| `SUPER` | 管理级操作（kill连接等） | 全局 |
| `REPLICATION SLAVE` | 从库复制 | 全局 |
| `REPLICATION CLIENT` | 查看主从状态 | 全局 |
| `SHOW DATABASES` | 查看数据库列表 | 全局 |
| `CREATE VIEW` | 创建视图 | 全局/库/表 |
| `EXECUTE` | 执行存储过程 | 存储过程 |

---

## 三、授权（GRANT）

### 1. 全局权限

```sql
-- 给予所有库所有表的只读权限
GRANT SELECT ON *.* TO 'dev'@'localhost';

-- 给予所有权限（相当于 root 级别）
GRANT ALL PRIVILEGES ON *.* TO 'admin'@'localhost';
```

### 2. 数据库级权限

```sql
-- 对 mydb 数据库的所有操作权限
GRANT ALL PRIVILEGES ON mydb.* TO 'dev'@'localhost';

-- 只给查询权限
GRANT SELECT ON mydb.* TO 'readonly'@'%';
```

### 3. 表级权限

```sql
-- 对特定表的读写
GRANT SELECT, INSERT, UPDATE ON mydb.orders TO 'app'@'%';

-- 对特定表的只读
GRANT SELECT ON mydb.users TO 'analyst'@'%';
```

### 4. 列级权限

```sql
-- 只允许查询 users 表的 name 和 email 列
GRANT SELECT (name, email) ON mydb.users TO 'privacy'@'%';
```

### 5. GRANT 附带选项

```sql
-- WITH GRANT OPTION：允许该用户将自身权限转授给其他用户（慎用）
GRANT SELECT ON mydb.* TO 'manager'@'%' WITH GRANT OPTION;

-- 限制资源使用（MySQL 8.0 部分版本支持）
GRANT ALL ON mydb.* TO 'app'@'%'
  WITH MAX_QUERIES_PER_HOUR 1000
       MAX_UPDATES_PER_HOUR 100
       MAX_CONNECTIONS_PER_HOUR 10
       MAX_USER_CONNECTIONS 5;
```

---

## 四、撤销权限（REVOKE）

```sql
-- 撤销特定权限
REVOKE INSERT, UPDATE ON mydb.* FROM 'dev'@'localhost';

-- 撤销所有权限
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'dev'@'localhost';

-- 撤销资源限制
REVOKE ALL ON mydb.* FROM 'app'@'%';
```

---

## 五、查看权限

```sql
-- 查看某用户的所有权限
SHOW GRANTS FOR 'dev'@'localhost';

-- 查看当前用户的权限
SHOW GRANTS;

-- 从系统表中查询权限
SELECT * FROM mysql.user WHERE user = 'dev'\G
SELECT * FROM mysql.db WHERE user = 'dev'\G
SELECT * FROM mysql.tables_priv WHERE user = 'dev'\G
SELECT * FROM mysql.columns_priv WHERE user = 'dev'\G
```

---

## 六、角色管理（MySQL 8.0+）



MySQL 8.0 引入了角色（Role），类似于用户组，可以将权限集合赋予角色，再将角色赋予用户。

### 1. 创建与使用角色

```sql
-- 创建角色
CREATE ROLE 'app_read', 'app_write', 'app_admin';

-- 给角色授权
GRANT SELECT ON mydb.* TO 'app_read';
GRANT INSERT, UPDATE, DELETE ON mydb.* TO 'app_write';
GRANT ALL PRIVILEGES ON mydb.* TO 'app_admin';

-- 将角色赋给用户
GRANT 'app_read' TO 'reader'@'%';
GRANT 'app_read', 'app_write' TO 'developer'@'%';
GRANT 'app_admin' TO 'admin'@'%';
```

### 2. 激活角色

```sql
-- 用户登录后，需要激活角色才能使用
SET DEFAULT ROLE ALL TO 'developer'@'%';

-- 或者在会话中手动激活
SET ROLE 'app_read';
SET ROLE ALL;

-- 查看当前激活的角色
SELECT CURRENT_ROLE();
```

### 3. 撤销与删除角色

```sql
-- 从用户身上撤销角色
REVOKE 'app_write' FROM 'developer'@'%';

-- 删除角色
DROP ROLE 'app_read', 'app_write';
```

---

## 七、实战：典型权限配置方案

### 场景设计

```
├── dba_admin        → 全局管理权限
├── app_readwrite    → 业务库读写权限
├── app_readonly     → 业务库只读权限
├── backup_user      → 备份专用（SELECT + LOCK TABLES + RELOAD）
└── monitor_user     → 监控专用（PROCESS + REPLICATION CLIENT + SELECT on performance_schema）
```

```sql
-- 1. DBA 管理员
CREATE USER 'dba_admin'@'10.0.0.%' IDENTIFIED BY 'StrongPass#1';
GRANT ALL PRIVILEGES ON *.* TO 'dba_admin'@'10.0.0.%' WITH GRANT OPTION;

-- 2. 应用读写用户
CREATE USER 'app_rw'@'10.0.0.%' IDENTIFIED BY 'AppRW#2024';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, CREATE VIEW, SHOW VIEW
    ON mydb.* TO 'app_rw'@'10.0.0.%';

-- 3. 只读用户
CREATE USER 'app_ro'@'10.0.0.%' IDENTIFIED BY 'AppRO#2024';
GRANT SELECT ON mydb.* TO 'app_ro'@'10.0.0.%';

-- 4. 备份用户
CREATE USER 'backup'@'localhost' IDENTIFIED BY 'Backup#2024';
GRANT SELECT, SHOW VIEW, TRIGGER, LOCK TABLES, PROCESS, RELOAD ON *.* TO 'backup'@'localhost';

-- 5. 监控用户
CREATE USER 'monitor'@'10.0.0.%' IDENTIFIED BY 'Monitor#2024';
GRANT PROCESS, REPLICATION CLIENT, REPLICATION SLAVE ON *.* TO 'monitor'@'10.0.0.%';
GRANT SELECT ON performance_schema.* TO 'monitor'@'10.0.0.%';
GRANT SELECT ON sys.* TO 'monitor'@'10.0.0.%';

-- 6. 刷新权限
FLUSH PRIVILEGES;
```

---

## 八、安全最佳实践

| 实践 | 说明 |
|---|---|
| **最小权限原则** | 只授予完成工作所需的最小权限 |
| **限制 host 来源** | 不要用 `'%'`，尽量指定 IP/网段 |
| **强密码策略** | 启用 `validate_password` 组件 |
| **避免 WITH GRANT OPTION** | 除非确实需要，否则不授予转授权限 |
| **定期审计** | 定期检查 `mysql.user` 和权限分配 |
| **删除匿名用户** | 安装后立即删除 |
| **禁用远程 root** | root 只允许 localhost 登录 |
| **密码过期策略** | 使用 `ALTER USER ... PASSWORD EXPIRE` |

```sql
-- 删除匿名用户（安装后安全加固）
DROP USER ''@'localhost';
DROP USER ''@'%';

-- 删除测试数据库
DROP DATABASE IF EXISTS test;

-- 启用密码验证组件
INSTALL COMPONENT 'file://component_validate_password';
SET GLOBAL validate_password.length = 12;
SET GLOBAL validate_password.mixed_case_count = 1;
SET GLOBAL validate_password.number_count = 1;
SET GLOBAL validate_password.special_char_count = 1;

-- 设置密码过期
ALTER USER 'app'@'%' PASSWORD EXPIRE INTERVAL 90 DAY;

-- 锁定/解锁账户
ALTER USER 'temp_user'@'%' ACCOUNT LOCK;
ALTER USER 'temp_user'@'%' ACCOUNT UNLOCK;
```

---

## 九、权限生效机制

```
GRANT/REVOKE 执行后立即生效（无需 FLUSH）
├── 但推荐执行 FLUSH PRIVILEGES 确保内存与授权表同步
├── 已建立的连接保留原有权限，新连接使用新权限
└── mysql.user → mysql.db → mysql.tables_priv → mysql.columns_priv
    （优先级从高到低，取最精确的匹配）
```

```sql
-- FLUSH PRIVILEGES 什么时候真正需要？
-- → 直接修改 mysql.user / mysql.db 等系统表后必须执行
-- → 使用 GRANT/REVOKE 语句则自动生效，但习惯上可执行一次确保同步
FLUSH PRIVILEGES;
```

---

以上覆盖了 MySQL 用户与权限管理的核心内容。如果你有特定场景（比如主从复制权限、插件认证、LDAP 集成等），可以进一步探讨。
