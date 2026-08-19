---
title: MySQL-Proxy 实现读写分离
date: 2026-09-08 04:00:00
tags:
  - MySQL
  - 读写分离
  - 主从复制
  - DBA
categories:
  - MySQL
---

## 一、架构原理

```
                        ┌─────────────┐
       应用程序 ────────▶│ MySQL-Proxy │
                        │  (中间代理)  │
                        └──────┬──────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │  Master    │──▶│  Slave 1  │   │  Slave 2  │
        │  (主库)    │   │  (从库)   │   │  (从库)   │
        │  写操作    │   │  读操作   │   │  读操作   │
        └───────────┘   └───────────┘   └───────────┘
```

**核心思路：** MySQL-Proxy 位于客户端和数据库之间，拦截 SQL 语句，根据 SQL 类型（读/写）将请求路由到不同的后端服务器。

---

## 二、环境准备

### 1. 主从复制搭建（前置条件）

**Master（192.168.1.10）配置：**
```ini
# /etc/my.cnf
[mysqld]
server-id       = 1
log-bin         = mysql-bin
binlog-format   = ROW
```

**Slave（192.168.1.11）配置：**
```ini
# /etc/my.cnf
[mysqld]
server-id       = 2
relay-log       = relay-bin
read_only       = 1
```

**在 Master 上创建复制用户：**
```sql
CREATE USER 'repl'@'%' IDENTIFIED BY 'repl_password';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
```

**在 Slave 上配置复制：**
```sql
CHANGE MASTER TO
  MASTER_HOST     = '192.168.1.10',
  MASTER_USER     = 'repl',
  MASTER_PASSWORD = 'repl_password',
  MASTER_LOG_FILE = 'mysql-bin.000001',
  MASTER_LOG_POS  = 154;

START SLAVE;
SHOW SLAVE STATUS\G
```

### 2. 安装 MySQL-Proxy

```bash
# 下载（以 0.8.5 为例）
wget https://downloads.mysql.com/archives/get/file/mysql-proxy-0.8.5-linux-glibc2.12-x86-64bit.tar.gz

tar -zxvf mysql-proxy-0.8.5-linux-glibc2.12-x86-64bit.tar.gz
mv mysql-proxy-0.8.5-linux-glibc2.12-x86-64bit /usr/local/mysql-proxy

# 添加环境变量
echo 'export PATH=/usr/local/mysql-proxy/bin:$PATH' >> /etc/profile
source /etc/profile
```

---

## 三、Lua 读写分离脚本

创建核心的路由脚本：

```lua
-- /usr/local/mysql-proxy/share/rw_splitting.lua

-- ===================== 配置区 =====================
local PROXY_ADDRESS  = "0.0.0.0:3306"       -- 代理监听地址
local BACKENDS = {
    { host = "192.168.1.10", port = 3306, weight = 1 },  -- Master（写）
    { host = "192.168.1.11", port = 3306, weight = 2 },  -- Slave 1（读）
}
-- 权重越高，被选中读的概率越大

-- ===================== 状态追踪 =====================
local connected_clients = 0
local backend_index = 2  -- 读请求从第一个 Slave 开始（下标 2 = BACKENDS[2]）

-- ===================== 连接阶段 =====================
function connect_server()
    -- 默认指向 Master
    proxy.connection.backend_address = {
        host = BACKENDS[1].host,
        port = BACKENDS[1].port
    }
end

-- ===================== 读写判断核心 =====================
function read_query(packet)
    local query = string.sub(packet, 2)  -- 去掉命令类型字节

    -- 判断是否为写操作
    local is_write = false

    -- 匹配写操作关键词（不区分大小写）
    local upper_query = string.upper(query)

    -- 以这些关键词开头的都是写操作
    local write_keywords = {
        "INSERT", "UPDATE", "DELETE", "REPLACE",
        "ALTER",  "DROP",   "CREATE", "TRUNCATE",
        "GRANT",  "REVOKE", "RENAME"
    }

    for _, keyword in ipairs(write_keywords) do
        if string.find(upper_query, "^%s*" .. keyword) then
            is_write = true
            break
        end
    end

    -- ========== 根据类型路由 ==========
    if is_write then
        -- 写操作 → Master
        print("[RW-SPLIT] WRITE → Master (" .. BACKENDS[1].host .. ")")
        proxy.connection.backend_address = {
            host = BACKENDS[1].host,
            port = BACKENDS[1].port
        }
    else
        -- 读操作 → Slave（简单轮询）
        local slave = BACKENDS[backend_index]
        print("[RW-SPLIT] READ  → Slave (" .. slave.host .. ")")
        proxy.connection.backend_address = {
            host = slave.host,
            port = slave.port
        }

        -- 轮询下一个 Slave
        backend_index = backend_index + 1
        if backend_index > #BACKENDS then
            backend_index = 2  -- 回到第一个 Slave
        end
    end

    -- 放行 SQL
    return proxy.PROXY_SEND_QUERY
end
```

---

## 四、更完善的生产级 Lua 脚本

```lua
-- /usr/local/mysql-proxy/share/rw_splitting.lua

-- ======================================================
-- 生产级读写分离脚本
-- 功能：读写分离 + 事务感知 + 负载均衡 + 连接池
-- ======================================================

local MASTER = { host = "192.168.1.10", port = 3306 }
local SLAVES = {
    { host = "192.168.1.11", port = 3306 },
    { host = "192.168.1.12", port = 3306 },
}

-- 每个客户端连接维护自己的状态
local client_state = {}

-- ===================== 工具函数 =====================
local function get_client_id()
    return proxy.connection.client.src.address .. ":" .. proxy.connection.client.src.port
end

local function get_state()
    local id = get_client_id()
    if not client_state[id] then
        client_state[id] = {
            in_transaction = false,
            slave_index    = 1,
        }
    end
    return client_state[id]
end

local function choose_slave(state)
    local idx = state.slave_index
    local slave = SLAVES[idx]
    state.slave_index = (idx % #SLAVES) + 1
    return slave
end

local function is_write_query(query)
    local upper = string.upper(query)

    -- DML / DDL 写操作
    local write_patterns = {
        "^%s*INSERT",
        "^%s*UPDATE",
        "^%s*DELETE",
        "^%s*REPLACE",
        "^%s*ALTER",
        "^%s*DROP",
        "^%s*CREATE",
        "^%s*TRUNCATE",
        "^%s*RENAME",
        "^%s*GRANT",
        "^%s*REVOKE",
        "^%s*CALL",          -- 存储过程可能有写操作
        "^%s*LOCK%s+TABLE",
    }

    for _, pattern in ipairs(write_patterns) do
        if string.find(upper, pattern) then
            return true
        end
    end

    -- SELECT ... FOR UPDATE / LOCK IN SHARE MODE
    if string.find(upper, "FOR%s+UPDATE") or
       string.find(upper, "LOCK%s+IN%s+SHARE%s+MODE") then
        return true
    end

    return false
end

local function is_transaction_cmd(query)
    local upper = string.upper(query)
    return string.find(upper, "^%s*BEGIN") or
           string.find(upper, "^%s*START%s+TRANSACTION") or
           string.find(upper, "^%s*SET%s+AUTOCOMMIT%s*=%s*0")
end

local function is_commit_or_rollback(query)
    local upper = string.upper(query)
    return string.find(upper, "^%s*COMMIT") or
           string.find(upper, "^%s*ROLLBACK")
end

-- ===================== 连接管理 =====================

function disconnect_client()
    local id = get_client_id()
    client_state[id] = nil
    print("[RW-SPLIT] Client disconnected: " .. id)
end

-- ===================== 核心路由逻辑 =====================

function read_query(packet)
    local query = string.sub(packet, 2)
    local state = get_state()

    -- 1) 事务开始 → 标记并路由到 Master
    if is_transaction_cmd(query) then
        state.in_transaction = true
        proxy.connection.backend_address = MASTER
        print("[RW-SPLIT] TX BEGIN → Master")
        return proxy.PROXY_SEND_QUERY
    end

    -- 2) 事务结束 → 清除标记，路由到 Master
    if is_commit_or_rollback(query) then
        state.in_transaction = false
        proxy.connection.backend_address = MASTER
        print("[RW-SPLIT] TX END   → Master")
        return proxy.PROXY_SEND_QUERY
    end

    -- 3) 事务中 → 所有操作都在 Master
    if state.in_transaction then
        proxy.connection.backend_address = MASTER
        print("[RW-SPLIT] IN TX   → Master")
        return proxy.PROXY_SEND_QUERY
    end

    -- 4) 写操作 → Master
    if is_write_query(query) then
        proxy.connection.backend_address = MASTER
        print("[RW-SPLIT] WRITE   → Master (" .. MASTER.host .. ")")
        return proxy.PROXY_SEND_QUERY
    end

    -- 5) 读操作 → Slave（轮询）
    local slave = choose_slave(state)
    proxy.connection.backend_address = slave
    print("[RW-SPLIT] READ    → Slave (" .. slave.host .. ")")
    return proxy.PROXY_SEND_QUERY
end

-- ===================== 错误处理 =====================

function read_query_result(inj)
    local res = proxy.MYSQLD_INJECT_RESULT

    -- 如果 Slave 查询失败，尝试回退到 Master
    if res == proxy.MYSQLD_INJECT_RESULT_ERROR then
        local state = get_state()
        local err_code = proxy.MYSQLD_ERR

        print("[RW-SPLIT] Error from backend, code: " .. tostring(err_code))

        -- 1227 = Access denied, 1290 = read-only
        if err_code == 1227 or err_code == 1290 then
            print("[RW-SPLIT] Failover → Master")
            proxy.connection.backend_address = MASTER
            return proxy.PROXY_SEND_QUERY
        end
    end

    return proxy.PROXY_SEND_QUERY
end
```

---

## 五、启动 MySQL-Proxy

### 方式一：命令行启动

```bash
mysql-proxy \
  --proxy-address=0.0.0.0:3306 \
  --proxy-backend-addresses=192.168.1.10:3306 \
  --proxy-read-only-backend-addresses=192.168.1.11:3306 \
  --proxy-lua-script=/usr/local/mysql-proxy/share/rw_splitting.lua \
  --log-file=/var/log/mysql-proxy.log \
  --log-level=info \
  --daemon
```

**参数说明：**

| 参数 | 说明 |
|---|---|
| `--proxy-address` | Proxy 监听地址 |
| `--proxy-backend-addresses` | 后端主库地址 |
| `--proxy-read-only-backend-addresses` | 后端从库地址 |
| `--proxy-lua-script` | Lua 路由脚本 |
| `--daemon` | 后台运行 |

### 方式二：systemd 管理

```ini
# /etc/systemd/system/mysql-proxy.service
[Unit]
Description=MySQL Proxy
After=network.target mysql.service

[Service]
Type=forking
ExecStart=/usr/local/mysql-proxy/bin/mysql-proxy \
    --proxy-address=0.0.0.0:3306 \
    --proxy-backend-addresses=192.168.1.10:3306 \
    --proxy-read-only-backend-addresses=192.168.1.11:3306 \
    --proxy-lua-script=/usr/local/mysql-proxy/share/rw_splitting.lua \
    --log-file=/var/log/mysql-proxy.log \
    --log-level=info \
    --daemon
ExecStop=/bin/kill $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl start mysql-proxy
systemctl enable mysql-proxy
```

---

## 六、验证读写分离

```bash
# 连接 Proxy（不是直接连数据库）
mysql -u root -p -h 192.168.1.20 -P 3306
```

```sql
-- 写操作 → 应路由到 Master
INSERT INTO test.user(name) VALUES('Alice');
UPDATE test.user SET name='Bob' WHERE id=1;

-- 读操作 → 应路由到 Slave
SELECT * FROM test.user;
SELECT COUNT(*) FROM test.user;
```

**查看日志确认路由：**
```bash
tail -f /var/log/mysql-proxy.log

# 预期输出：
# [RW-SPLIT] WRITE  → Master (192.168.1.10)
# [RW-SPLIT] READ   → Slave (192.168.1.11)
# [RW-SPLIT] READ   → Slave (192.168.1.12)
```

---

## 七、注意事项与局限性

### 存在的问题

```
┌──────────────────────────────────────────────────────────┐
│              MySQL-Proxy 已知局限                         │
├──────────────────────────────────────────────────────────┤
│ 1. 官方已停止维护（最后版本 0.8.5，发布于 2014 年）       │
│ 2. 性能瓶颈明显，高并发下延迟增大                         │
│ 3. 单点故障风险，需额外做 HA                              │
│ 4. Lua 脚本处理复杂 SQL 可能误判                          │
│ 5. 不支持连接池（0.8.x 部分支持）                         │
└──────────────────────────────────────────────────────────┘
```

### 主从同步延迟问题

```
写入 Master ──→ 主从同步延迟 ──→ 立即读 Slave → 可能读到旧数据

解决方案：
  1. 写后读走 Master（在事务中读）
  2. 使用半同步复制降低延迟
  3. 应用层引入短暂延迟（sleep）
```

---

## 八、更推荐的替代方案

| 方案 | 特点 | 适用场景 |
|---|---|---|
| **ProxySQL** | 活跃维护，连接池，查询缓存，规则引擎 | 生产环境首选 |
| **MaxScale** | MariaDB 官方，功能强大 | 大规模集群 |
| **MySQL Router** | MySQL 官方，InnoDB Cluster 配套 | InnoDB Cluster |
| **MyCat** | 国产中间件，分库分表+读写分离 | 分库分表场景 |
| **ShardingSphere** | Apache 项目，Java 生态，功能全面 | Java 技术栈 |

### ProxySQL 示例（推荐替代）

```sql
-- ProxySQL 配置读写分离（对比 MySQL-Proxy 的复杂 Lua 脚本）
-- 添加后端 MySQL 实例
INSERT INTO mysql_servers(hostgroup_id, hostname, port)
VALUES
  (10, '192.168.1.10', 3306),  -- Writer 组
  (20, '192.168.1.11', 3306),  -- Reader 组
  (20, '192.168.1.12', 3306);  -- Reader 组

-- 配置路由规则
INSERT INTO mysql_query_rules(rule_id, match_pattern, destination_hostgroup)
VALUES
  (1, '^SELECT.*FOR UPDATE', 10),   -- SELECT FOR UPDATE → Writer
  (2, '^SELECT',              20);  -- 普通 SELECT → Reader
-- 其他语句默认走 Writer 组

LOAD MYSQL SERVERS TO RUNTIME;
LOAD MYSQL QUERY RULES TO RUNTIME;
SAVE MYSQL SERVERS TO DISK;
SAVE MYSQL QUERY RULES TO DISK;
```

---

## 总结

MySQL-Proxy 可以实现读写分离的**基本功能**，核心原理就是通过 Lua 脚本拦截 SQL，按类型路由到 Master/Slave。但由于该项目**已长期停止维护**，生产环境建议使用 **ProxySQL** 或 **MaxScale** 等活跃维护的替代方案。
