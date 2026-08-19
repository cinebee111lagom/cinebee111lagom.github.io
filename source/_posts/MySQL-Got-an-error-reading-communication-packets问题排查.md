---
title: MySQL Got an error reading communication packets问题排查
date: 2026-09-08 05:00:00
tags:
  - MySQL
  - 故障排查
  - 网络
  - DBA
categories:
  - MySQL
---

## 错误含义

这个错误记录在 MySQL **错误日志**中，表示 MySQL 服务端在读取客户端发来的数据包时遇到了问题——要么包不完整，要么连接异常中断。

---

## 常见原因

### 1. 数据包过大（最常见）

客户端发送的数据超过了 MySQL 允许的大小限制。

```sql
-- 查看当前限制
SHOW VARIABLES LIKE 'max_allowed_packet';

-- 临时调大（会话级别）
SET GLOBAL max_allowed_packet = 256 * 1024 * 1024;  -- 256MB
```

**永久生效**需修改 `my.cnf`：

```ini
[mysqld]
max_allowed_packet = 256M
```

---

### 2. 连接超时 / 连接未正常关闭

客户端连接超时后直接断开，MySQL 还在等待数据。

```sql
-- 查看超时设置
SHOW VARIABLES LIKE 'wait_timeout';
SHOW VARIABLES LIKE 'interactive_timeout';

-- 适当调大
SET GLOBAL wait_timeout = 600;
SET GLOBAL interactive_timeout = 600;
```

---

### 3. 应用程序连接泄漏

应用获取连接后未正确关闭，导致连接悬挂。

**排查方式：**
```sql
-- 查看当前连接状态
SHOW FULL PROCESSLIST;

-- 关注这些状态
-- "Sleep" 且 Time 很大 → 连接未释放
-- 连接数异常多 → 可能存在泄漏
```

**检查应用代码**，确保使用了连接池并正确归还连接：
```java
// Java 示例：使用 try-with-resources
try (Connection conn = dataSource.getConnection();
     PreparedStatement ps = conn.prepareStatement(sql)) {
    // ...
}  // 自动关闭
```

---

### 4. 网络问题

网络不稳定、防火墙中断、DNS 解析缓慢等。

```bash
# 检查网络连通性
ping <mysql_host>
telnet <mysql_host> 3306

# 检查是否有丢包
ping -c 100 <mysql_host> | tail -1
```

**调整 net_read / net_write 超时：**
```ini
[mysqld]
net_read_timeout = 120
net_write_timeout = 120
```

---

### 5. DNS 解析问题

MySQL 默认会对每个连接做 DNS 反解析，DNS 慢或失败会导致问题。

```ini
[mysqld]
skip-name-resolve
```

---

### 6. 线程栈空间不足

```ini
[mysqld]
thread_stack = 512K
```

---

## 排查步骤总结

```
1. 查看错误日志，确认报错频率和模式
   └─ tail -f /var/log/mysql/error.log

2. 检查 max_allowed_packet 是否太小
   └─ SHOW VARIABLES LIKE 'max_allowed_packet';

3. 检查当前连接数和连接状态
   └─ SHOW STATUS LIKE 'Threads_connected';
   └─ SHOW FULL PROCESSLIST;

4. 检查应用端是否有连接泄漏
   └─ 连接池监控 + 代码审查

5. 检查网络质量
   └─ ping / telnet / 抓包 (tcpdump)

6. 调整关键参数后重启 MySQL 验证
```

---

## 推荐的 my.cnf 配置模板

```ini
[mysqld]
# 数据包大小
max_allowed_packet     = 256M

# 超时设置
wait_timeout           = 600
interactive_timeout    = 600
net_read_timeout       = 120
net_write_timeout      = 120

# 跳过 DNS 解析
skip-name-resolve

# 线程栈
thread_stack           = 512K
```

---

## 关键提醒

- 如果这个错误**偶尔出现**，通常是客户端主动断开连接，属于正常现象，不需要特别处理。
- 如果**频繁出现**（大量刷屏），就需要排查了——大概率是 `max_allowed_packet` 太小或应用连接管理有问题。
- 修改配置后记得 `systemctl restart mysqld` 或执行 `SET GLOBAL` 使其生效。

你的环境具体是什么场景下出现的？是偶尔还是频繁？用的什么客户端？我可以帮你进一步定位。
