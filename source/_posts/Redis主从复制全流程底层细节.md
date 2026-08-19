---
title: Redis 主从复制全流程底层细节
date: 2026-09-07 20:30:00
tags:
  - Redis
  - 主从复制
  - 底层原理
categories:
  - 缓存架构
---

## 一、从节点发起连接

### 1. 入口：REPLICAOF 命令

```c
// src/replication.c
void replicaofCommand(client *c) {
    // REPLICAOF NO ONE → 将当前节点提升为主节点
    if (!strcasecmp(c->argv[1]->ptr,"no") &&
        !strcasecmp(c->argv[2]->ptr,"one")) 
    {
        // ... 晋升逻辑
        return;
    }

    // REPLICAOF <host> <port> → 将当前节点设为从节点
    char *host = c->argv[1]->ptr;
    int port;
    if ((port = atoi(c->argv[2]->ptr)) == 0) {
        addReplyError(c,"Invalid port number");
        return;
    }

    // 如果已经是该主节点的从节点，直接返回
    if (server.masterhost && !strcasecmp(server.masterhost, host)
        && server.masterport == port) 
    {
        addReply(c, shared.ok);
        return;
    }

    // 设置主节点信息
    sdsfree(server.masterhost);
    server.masterhost = sdsdup(host);
    server.masterport = port;

    // 断开与旧主节点的连接
    if (server.master) freeClient(server.master);

    // 关键：将复制状态设为 CONNECT
    // replicationCron() 会检测这个状态并发起连接
    server.repl_state = REPL_STATE_CONNECT;

    // 取消正在进行的 RDB 传输
    if (server.rdb_child_pid != -1) {
        kill(server.rdb_child_pid, SIGUSR1);
    }

    addReply(c, shared.ok);
}
```

### 2. 定时任务驱动连接

```c
// src/replication.c — 每秒执行一次
void replicationCron(void) {
    // ...

    /* 如果处于 CONNECT 状态，尝试建立连接 */
    if (server.masterhost &&
        server.repl_state == REPL_STATE_CONNECT) 
    {
        serverLog(LL_NOTICE, "Connecting to MASTER %s:%d",
            server.masterhost, server.masterport);
        connectWithMaster();  // ← 发起 TCP 连接
    }

    /* 如果连接已断开，定期重试 */
    if (server.masterhost &&
        (server.repl_state == REPL_STATE_CONNECTING ||
         (server.repl_state == REPL_STATE_TRANSFER &&
          (time(NULL) - server.repl_transfer_lastio) > 
          server.repl_timeout)))
    {
        // 超时处理：断开并重试
        if (server.master) freeClient(server.master);
        // ...
        server.repl_state = REPL_STATE_CONNECT;
    }

    // ...
}
```

### 3. connectWithMaster() — TCP 连接建立

```c
// src/replication.c
int connectWithMaster(void) {
    // 创建非阻塞 socket 并连接主节点
    int fd = anetTcpNonBlockConnect(server.neterr,
        server.masterhost, server.masterport);

    // 创建 connection 对象（Redis 6.0+ 统一连接抽象）
    connection *conn = connCreate(Socket);
    connSetPrivateData(conn, server.master);

    // 注册连接事件回调
    // 连接成功后 → syncWithMaster() 被调用
    if (connConnect(conn, server.masterhost, server.masterport,
        server.bind_source_addr, syncWithMaster) == C_ERR) 
    {
        serverLog(LL_WARNING, "Unable to connect to MASTER: %s",
            server.neterr);
        return C_ERR;
    }

    // 更新复制状态
    server.repl_state = REPL_STATE_CONNECTING;
    server.repl_down_since = 0;

    return C_OK;
}
```

```
TCP 连接建立的底层过程：

从节点                                主节点
  |                                      |
  | socket() → fd                        |
  | connect(fd, master_ip, master_port)  |
  | ──── TCP SYN ─────────────────────→  |
  |                                      | accept()
  | ←─── TCP SYN+ACK ──────────────────|
  | ──── TCP ACK ─────────────────────→  |
  |                                      |
  |  epoll 触发可写事件                   |
  |  → 回调 syncWithMaster()             |
  |                                      |
```

### 4. syncWithMaster() — 握手阶段

```c
// src/replication.c
void syncWithMaster(connection *conn) {
    // ...

    /* Step 1: 发送 PING */
    err = sendCommand(conn, "PING", NULL);
    if (err) goto error;

    server.repl_state = REPL_STATE_RECEIVE_PONG;
    // 等待主节点回复 PONG...
}

// 主节点回复 PONG 后的处理
// (由 installIOHandler / readQueryFromMaster 驱动状态机继续)
```

### 5. 完整握手状态机

```c
// src/replication.c — 从节点复制状态机
// 以下函数在不同阶段被事件驱动调用

// 状态流转：

// REPL_STATE_CONNECT
//   → connectWithMaster() 
//   → REPL_STATE_CONNECTING

// REPL_STATE_CONNECTING  (等待 TCP 连接完成)
//   → 连接成功 → syncWithMaster()
//   → 发送 PING
//   → REPL_STATE_RECEIVE_PONG

// REPL_STATE_RECEIVE_PONG
//   → 收到 +PONG
//   → 如果主节点配置了密码，发送 AUTH <password>
//   → REPL_STATE_SEND_AUTH / REPL_STATE_RECEIVE_AUTH

// AUTH 完成后 (或无需 AUTH)
//   → 发送 REPLCONF listening-port <从节点端口>
//   → REPL_STATE_SEND_PORT

// REPL_STATE_SEND_PORT 收到 +OK
//   → 发送 REPLCONF ip-address <从节点IP>
//   → REPL_STATE_SEND_IP

// REPL_STATE_SEND_IP 收到 +OK
//   → 发送 REPLCONF capa eof capa psync2
//   → REPL_STATE_SEND_CAPA

// REPL_STATE_SEND_CAPA 收到 +OK
//   → 发送 PSYNC <runid> <offset>
//   → REPL_STATE_SEND_PSYNC

// REPL_STATE_SEND_PSYNC
//   → 收到响应 → REPL_STATE_RECEIVE_PSYNC
//   → 根据响应类型分流：
//       +FULLRESYNC → 全量同步 → REPL_STATE_TRANSFER
//       +CONTINUE   → 增量同步 → REPL_STATE_CONNECTED
```

```c
// src/replication.c — 每个状态的具体处理
void replicationDiscardCachedMaster(void) { /* ... */ }

// 安装 I/O 处理器 → 所有后续通信通过此函数驱动
void installIOHandler(void) {
    // 注册可读事件
    // 当主节点发来数据时 → readQueryFromMaster() 被调用
    connSetReadHandler(server.master, readQueryFromMaster);
    // 这个函数内部驱动整个状态机
}

void readQueryFromMaster(connection *conn) {
    // 读取主节点发来的数据
    nread = connRead(conn, c->querybuf + qblen, readlen);

    // 根据当前 repl_state 处理不同阶段的响应
    if (server.repl_state == REPL_STATE_RECEIVE_PONG) {
        // 处理 PONG 响应
        // ...
        server.repl_state = REPL_STATE_SEND_AUTH;
    }
    // ... 其他状态处理

    // 最终进入 CONNECTED 状态后
    // 所有数据通过 processInputBuffer() 处理（和普通客户端一样）
}
```

---

## 二、PSYNC 命令的关键参数

### 1. PSYNC 命令的发送

```c
// src/replication.c
void sendPSYNC(void) {
    // 首次同步：
    //   PSYNC ? -1
    //   runid = "?" (不知道主节点的 runid)
    //   offset = -1 (没有已同步的数据)

    // 断线重连：
    //   PSYNC <cached_master_replid> <reploff>
    //   runid = 上次连接的主节点的 replid
    //   offset = 上次同步到的 offset

    int psync_result;

    if (server.cached_master) {
        // 有缓存的主节点信息（断线重连）
        psync_result = slaveTryPartialResynchronization(
            fd, server.cached_master->reploff);
        // 发送: PSYNC <cached_master_replid> <cached_master_reploff>
    } else {
        // 首次连接
        psync_result = slaveTryPartialResynchronization(fd, -1);
        // 发送: PSYNC ? -1
    }
}

int slaveTryPartialResynchronization(int fd, long long repl_offset) {
    char *runid;
    int psync_len;

    if (repl_offset == -1) {
        // 首次同步
        runid = "?";
        repl_offset = -1;
    } else {
        // 断线重连：使用缓存的主节点信息
        runid = server.cached_master->replid;
        // repl_offset 已经传入
    }

    // 发送命令
    psync_len = snprintf(psync_cmd, sizeof(psync_cmd),
        "PSYNC %s %lld\r\n", runid, repl_offset);

    // 写入 socket
    if (syncWrite(fd, psync_cmd, psync_len, server.repl_timeout) 
        == -1) 
    {
        return PSYNC_WRITE_ERROR;
    }

    return PSYNC_WAIT_REPLY;
}
```

### 2. 主节点接收 PSYNC 并处理

```c
// src/replication.c
void replicationCommand(client *c) {
    // ...
    if (!strcasecmp(c->argv[0]->ptr, "psync")) {
        // PSYNC <runid> <offset>
        masterTryPartialResynchronization(c);
        return;
    }
}

int masterTryPartialResynchronization(client *c) {
    long long psync_offset;
    char *master_replid = c->argv[1]->ptr;

    // 解析 offset 参数
    if (c->argc == 3) {
        psync_offset = strtoll(c->argv[2]->ptr, NULL, 10);
    } else {
        psync_offset = -1;
    }

    // 如果这是新连接的从节点，记录日志
    if (c->flags & CLIENT_MASTER) {
        // ... 特殊处理
    }

    // ============================================================
    // 判断1: replid 完全匹配当前节点的 replid
    // ============================================================
    if (!strcmp(master_replid, server.replid)) {
        // replid 匹配，检查 offset

        if (!server.repl_backlog) {
            // 没有 backlog → 无法增量同步
            serverLog(LL_NOTICE,
                "Partial resynchronization not accepted (backlog not enabled)");
            goto need_full_resync;
        }

        // 检查 offset 是否在 backlog 有效范围内
        // backlog 有效范围 = [repl_backlog_off, repl_backlog_off + repl_backlog_histlen]
        if (psync_offset < server.repl_backlog_off ||
            psync_offset > (server.repl_backlog_off + 
                           server.repl_backlog_histlen))
        {
            serverLog(LL_NOTICE,
                "Partial resynchronization not accepted "
                "(requested offset: %lld, backlog offset: %lld)",
                psync_offset, server.repl_backlog_off);
            goto need_full_resync;
        }

        // 增量同步成功！
        // 注册从节点到 slaves 列表
        c->flags |= CLIENT_SLAVE;
        c->replstate = SLAVE_STATE_ONLINE;
        c->repl_ack_time = server.unixtime;
        c->repl_put_online_on_ack = 0;

        listAddNodeTail(server.slaves, c);

        // 回复 +CONTINUE
        addReply(c, shared.psynccnt);

        // 发送 backlog 中缺失的数据
        addReplyReplicationBacklog(c, psync_offset);

        serverLog(LL_NOTICE,
            "Partial resynchronization request from %s accepted. "
            "Sending %lld bytes of backlog starting from offset %lld.",
            replicationGetSlaveName(c),
            server.master_repl_offset - psync_offset,
            psync_offset);

        return PSYNC_CONTINUE;
    }

    // ============================================================
    // 判断2: replid 匹配 replid2 (PSYNC2)
    // ============================================================
    if (!strcmp(master_replid, server.replid2)) {
        // 检查 offset 是否在 replid2 有效范围内
        if (psync_offset <= server.second_replid_offset) {
            // 还需要检查是否在 backlog 物理范围内
            if (!server.repl_backlog ||
                psync_offset < server.repl_backlog_off ||
                psync_offset > (server.repl_backlog_off + 
                               server.repl_backlog_histlen))
            {
                goto need_full_resync;
            }

            // PSYNC2 增量同步！
            c->flags |= CLIENT_SLAVE;
            c->replstate = SLAVE_STATE_ONLINE;
            listAddNodeTail(server.slaves, c);

            addReply(c, shared.psynccnt);
            addReplyReplicationBacklog(c, psync_offset);

            return PSYNC_CONTINUE;
        }
    }

    // ============================================================
    // 判断3: 都不匹配 → 全量同步
    // ============================================================
need_full_resync:
    // ...
    // 更新 replid2
    memcpy(server.replid2, server.replid, sizeof(server.replid));
    server.second_replid_offset = server.master_repl_offset + 1;

    // 生成新 replid（如果是全新主节点才需要）
    // 实际上这里不会重新生成，只在 SLAVEOF NO ONE 时才生成
    // 此处只是记录日志

    // 回复 +FULLRESYNC <replid> <offset>
    sds reply = sdscatprintf(sdsempty(),
        "+FULLRESYNC %s %lld\r\n",
        server.replid, server.master_repl_offset);
    addReplySds(c, reply);

    // 标记从节点等待全量同步
    c->replstate = SLAVE_STATE_WAIT_BGSAVE_START;

    // 如果有其他从节点正在进行 BGSAVE，可以复用（取决于配置）
    // ...

    // 触发 BGSAVE
    startBgsaveForReplication(c->argc, c->argv);

    return PSYNC_FULLRESYNC;
}
```

### 3. 从节点收到 PSYNC 响应

```c
// src/replication.c
// 从节点在 REPL_STATE_RECEIVE_PSYNC 阶段处理响应

int slaveTryPartialResynchronization(int fd, long long repl_offset) {
    // ... 发送 PSYNC 之后，读取响应 ...

    char buf[256];
    int nread = syncReadLine(fd, buf, sizeof(buf), server.repl_timeout);

    // 解析响应
    if (!strncmp(buf, "+FULLRESYNC", 11)) {
        // 全量同步
        // 解析 runid 和 offset
        char *replid = buf + 12;
        char *offset_ptr = strchr(replid, ' ');
        *offset_ptr = '\0';
        offset_ptr++;

        // 保存主节点的 replid 和 offset
        memcpy(server.master_replid, replid, 
               CONFIG_RUN_ID_SIZE);
        server.master_initial_offset = strtoll(offset_ptr, NULL, 10);

        // 准备接收 RDB
        return PSYNC_FULLRESYNC;
    }

    if (!strncmp(buf, "+CONTINUE", 9)) {
        // 增量同步
        // 检查是否包含 replid (PSYNC2 响应可能带 replid)
        if (buf[9] == ' ') {
            memcpy(server.master_replid, buf + 10,
                   CONFIG_RUN_ID_SIZE);
        }
        return PSYNC_CONTINUE;
    }

    if (buf[0] == '-') {
        // 错误 (如 -ERR ...)
        serverLog(LL_WARNING,
            "Master does not support PSYNC or is in "
            "error state: %s", buf);
        return PSYNC_NOT_SUPPORTED;
    }

    // 未知响应
    return PSYNC_TRY_LATER;
}
```

### 4. PSYNC 参数含义总结

```
┌──────────────────────────────────────────────────────────────┐
│ PSYNC <runid> <offset>                                       │
│                                                              │
│ runid:                                                       │
│   "?"       → 首次同步，不知道主节点 runid                    │
│   "aaa..."  → 断线重连，携带上次主节点的 replid               │
│                                                              │
│ offset:                                                      │
│   -1        → 首次同步，没有已同步数据                        │
│   12345     → 断线重连，上次同步到的 master_repl_offset        │
│                                                              │
│ 响应：                                                       │
│   +FULLRESYNC <runid> <offset>                               │
│     → 主节点告诉从节点"你要全量同步"                           │
│     → runid: 主节点当前 replid（从节点保存备用）               │
│     → offset: 全量同步后的起始 offset（RDB 头部也会记录）      │
│                                                              │
│   +CONTINUE [<replid>]                                       │
│     → 主节点告诉从节点"增量同步即可"                           │
│     → 可选携带 replid（PSYNC2 场景）                           │
│                                                              │
│   -ERR ...                                                   │
│     → 主节点不支持 PSYNC（旧版本）                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、全量同步（Full Resync）底层

### 1. 主节点触发 BGSAVE

```c
// src/replication.c
int startBgsaveForReplication(int mincapa, int mincapa_slave) {
    int retval;
    int socket_target = 0;
    rdbSaveInfo rsi = RDB_SAVE_INFO_INIT;

    // 填充 rsi（RDB 保存信息）
    // rsi 中携带当前的 replid 和 offset
    rsi.repl_stream_db = server.slaveseldb;

    // 选择同步方式：socket 直传 or 写磁盘
    if (server.repl_diskless_sync) {
        socket_target = 1;  // 无盘复制
    }

    // 启动 BGSAVE 子进程
    if (socket_target) {
        // 无盘复制：RDB 通过 pipe 写到主进程，主进程直接网络传输
        retval = rdbSaveToSlavesSockets(&rsi);
    } else {
        // 有盘复制：RDB 写到磁盘文件
        retval = rdbSaveBackground(server.rdb_filename, &rsi);
    }

    if (retval == C_OK) {
        // BGSAVE 已启动
        // 更新所有等待中的从节点状态
        listIter li;
        listRewind(server.slaves, &li);
        while ((ln = listNext(&li))) {
            client *slave = listNodeValue(ln);
            if (slave->replstate == SLAVE_STATE_WAIT_BGSAVE_START) {
                if (socket_target) {
                    slave->replstate = SLAVE_STATE_WAIT_BGSAVE_END;
                    // 记录将要发送给该从节点的 fd
                } else {
                    slave->replstate = SLAVE_STATE_WAIT_BGSAVE_END;
                }
            }
        }
    }

    return retval;
}
```

### 2. BGSAVE 子进程执行

```c
// src/rdb.c
int rdbSaveBackground(char *filename, rdbSaveInfo *rsi) {
    // ...
    server.rdb_child_pid = redisFork(CHILD_TYPE_RDB);
    
    if (server.rdb_child_pid == 0) {
        /* 子进程 */
        // 关闭监听 socket，不影响主进程
        closeListeningSockets(0);
        
        // 设置进程标题
        redisSetProcTitle("redis-rdb-bgsave");
        
        // 执行 RDB 保存
        retval = rdbSave(filename, rsi);
        
        // 写完后退出
        exitFromChild((retval == C_OK) ? 0 : 1);
    } else if (server.rdb_child_pid > 0) {
        /* 主进程 */
        // 更新状态
        server.rdb_save_time_start = time(NULL);
        server.rdb_child_type = RDB_CHILD_TYPE_DISK;
        return C_OK;
    } else {
        /* fork 失败 */
        return C_ERR;
    }
}
```

### 3. RDB 文件结构

```c
// src/rdb.c — rdbSave() 核心逻辑

int rdbSave(char *filename, rdbSaveInfo *rsi) {
    // 打开临时文件
    FILE *fp = fopen(tmpfile, "w");
    rio rdb;
    rioInitWithFile(&rdb, fp);

    // ===== 第一部分：文件头 =====
    // "REDIS" + 版本号 (9字节)
    // 如: "REDIS0011" (版本 11 = Redis 7.0)
    rdbSaveType(&rdb, RDB_OPCODE_AUX);

    // ===== 第二部分：辅助字段 =====
    rdbSaveInfoAuxFields(&rdb, rsi, 0);
    // 写入:
    //   redis-ver = "7.0.0"
    //   redis-bits = "64"
    //   ctime = "1690000000"
    //   used-mem = "1073741824"
    //   repl-id = "<replid>"           ← 关键！
    //   repl-offset = "<offset>"       ← 关键！

    // ===== 第三部分：数据库数据 =====
    for (int j = 0; j < server.dbnum; j++) {
        redisDb *db = server.db+j;
        if (dictSize(db->dict) == 0) continue;

        // SELECTDB <dbid>
        rdbSaveType(&rdb, RDB_OPCODE_SELECTDB);
        rdbSaveLen(&rdb, j);

        // RESIZEDB <dict_size> <expires_size>
        rdbSaveType(&rdb, RDB_OPCODE_RESIZEDB);
        rdbSaveLen(&rdb, dictSize(db->dict));
        rdbSaveLen(&rdb, dictSize(db->expires));

        // 遍历所有 key
        dictIterator *di = dictGetIterator(db->dict);
        while ((de = dictNext(di)) != NULL) {
            sds key = dictGetKey(de);
            robj *val = dictGetVal(de);

            // 过期时间
            long long expiretime = getExpire(db, key);
            if (expiretime != -1) {
                rdbSaveType(&rdb, RDB_OPCODE_EXPIRETIME_MS);
                rdbSaveMillisecondTime(&rdb, expiretime);
            }

            // 序列化 key-value
            rdbSaveKeyValuePair(&rdb, key, val, expiretime, now);
        }
    }

    // ===== 第四部分：EOF 标记 =====
    rdbSaveType(&rdb, RDB_OPCODE_EOF);
    // 8 字节校验和 (CRC64)
    rdbSaveChecksum(&rdb, cksum);

    // 关闭文件，原子 rename
    fclose(fp);
    rename(tmpfile, filename);

    return C_OK;
}
```

```
RDB 文件物理布局：

┌────────────────────────────────────────────────────┐
│ REDIS0011                          (9B, magic+ver) │
├────────────────────────────────────────────────────┤
│ FA $redis-ver $7.0.0               (aux fields)    │
│ FA $redis-bits $64                                 │
│ FA $ctime $1690000000                              │
│ FA $used-mem $1073741824                           │
│ FA $repl-id $8371b4fb1155b71f4a04d3e1bc3e18c4...   │
│ FA $repl-offset $123456                            │
├────────────────────────────────────────────────────┤
│ FE 00                          (SELECTDB 0)        │
│ FB <dict_size> <expires_size>  (RESIZEDB)          │
├────────────────────────────────────────────────────┤
│ FD <expire_ms_high> <expire_ms_low>                │
│ 00 <type> <key> <value>    (key-value pair)        │
│ 00 <type> <key> <value>                            │
│ ...                                                │
├────────────────────────────────────────────────────┤
│ FE 01                          (SELECTDB 1)        │
│ ...                                                │
├────────────────────────────────────────────────────┤
│ FF                             (EOF opcode)        │
│ <8 bytes CRC64 checksum>                           │
└────────────────────────────────────────────────────┘
```

### 4. 主进程发送 RDB 给从节点

```c
// src/replication.c — BGSAVE 子进程完成后，主进程收到 SIGCHLD

void updateSlavesWaitingBgsave(int bgsaveerr, int type) {
    listIter li;
    listRewind(server.slaves, &li);

    while ((ln = listNext(&li))) {
        client *slave = listNodeValue(ln);

        if (slave->replstate == SLAVE_STATE_WAIT_BGSAVE_END) {
            if (bgsaveerr != C_OK) {
                freeClient(slave);
                continue;
            }

            // 打开 RDB 文件
            int dfd = -1;
            if (type == RDB_CHILD_TYPE_DISK) {
                dfd = open(server.rdb_filename, O_RDONLY);
                if (dfd == -1) {
                    freeClient(slave);
                    continue;
                }
            }

            // 设置从节点状态 → 开始发送
            slave->repldboff = 0;       // RDB 发送偏移量
            slave->repldbsize = ...;    // RDB 文件大小

            // 注册写事件回调：sendBulkToSlave()
            // 当 socket 可写时，sendBulkToSlave() 被调用
            if (connSetWriteHandler(slave->conn, 
                sendBulkToSlave) == C_ERR) 
            {
                close(dfd);
                freeClient(slave);
                continue;
            }

            // 保存 fd
            slave->repldbfd = dfd;
            slave->replstate = SLAVE_STATE_SEND_BULK;
            slave->replpreamble = sdsfromlonglong(
                slave->repldbsize);
        }
    }
}
```

### 5. RDB 传输的网络层 — sendBulkToSlave()

```c
// src/replication.c — 事件驱动的分块发送

void sendBulkToSlave(connection *conn) {
    client *slave = connGetPrivateData(conn);
    char buf[PROTO_IOBUF_LEN];  // 16KB 缓冲区
    ssize_t nwritten, buflen;

    // ===== 阶段1: 发送 RESP 大字符串前缀 =====
    // 发送 "$<rdb_size>\r\n"
    // 这是 RESP 协议的大块数据标记
    if (slave->replpreamble) {
        nwritten = connWrite(conn, slave->replpreamble,
                            sdslen(slave->replpreamble));
        if (nwritten <= 0) {
            // EAGAIN 或错误
            return;
        }
        sdsrange(slave->replpreamble, nwritten, -1);
        if (sdslen(slave->replpreamble) == 0) {
            sdsfree(slave->replpreamble);
            slave->replpreamble = NULL;
            // 进入下一阶段：发送 RDB 数据
        }
        return;
    }

    // ===== 阶段2: 分块读取 RDB 文件并发送 =====
    lseek(slave->repldbfd, slave->repldboff, SEEK_SET);
    buflen = read(slave->repldbfd, buf, sizeof(buf));

    if (buflen <= 0) {
        // 读取失败或 EOF
        serverLog(LL_WARNING, "Read error sending DB to replica: %s",
            (buflen == 0) ? "premature EOF" : strerror(errno));
        freeClient(slave);
        return;
    }

    // 写入网络 socket
    nwritten = connWrite(conn, buf, buflen);
    if (nwritten <= 0) {
        if (connGetState(conn) != CONN_STATE_CONNECTED) {
            serverLog(LL_WARNING,
                "Write error sending DB to replica: %s",
                strerror(errno));
            freeClient(slave);
        }
        return;
    }

    // 更新偏移量
    slave->repldboff += nwritten;

    // 更新最后 I/O 时间（用于超时检测）
    slave->repl_ack_time = server.unixtime;

    // ===== 阶段3: RDB 传输完成 =====
    if (slave->repldboff == slave->repldbsize) {
        close(slave->repldbfd);
        slave->repldbfd = -1;

        // 从 READ 事件切换到 WRITE 事件
        // 之后发送 backlog 中缓存的增量数据
        connSetWriteHandler(slave->conn, NULL);

        // 标记从节点已在线
        slave->replstate = SLAVE_STATE_ONLINE;
        slave->repl_put_online_on_ack = 1;

        // 设置写处理器，将缓冲区中的增量数据发送出去
        connSetWriteHandlerWithBarrier(slave->conn,
            sendReplyToClient, 1);
    }
}
```

### 6. 从节点接收 RDB

```c
// src/replication.c — 从节点侧接收

void readSyncBulkPayload(connection *conn) {
    // repl_state == REPL_STATE_TRANSFER

    // ===== 阶段1: 读取 RESP 前缀 "$<size>\r\n" =====
    if (server.repl_transfer_size == -1) {
        // 还不知道 RDB 大小
        // 读取第一行："$12345678\r\n"
        nread = connRead(conn, buf, 1024);
        
        // 解析 '$' 和数字
        char *p = strchr(buf, '\r');
        *p = '\0';
        server.repl_transfer_size = strtoll(buf + 1, NULL, 10);
        // 跳过 \r\n
    }

    // ===== 阶段2: 读取 RDB 数据并写入临时文件 =====
    nread = connRead(conn, buf, readlen);
    
    // 写入临时文件
    server.repl_transfer_lastio = server.unixtime;
    if (write(server.repl_transfer_fd, buf, nread) != nread) {
        // 写入失败
        serverLog(LL_WARNING, "Write error to RDB file: %s",
            strerror(errno));
        cancelReplicationHandshake(1);
        return;
    }

    server.repl_transfer_read += nread;

    // 更新复制进度（用于 INFO replication 显示）
    // repl_transfer_percent = read / size * 100

    // ===== 阶段3: RDB 全部接收完成 =====
    if (server.repl_transfer_read == server.repl_transfer_size) {
        // syncRead 完成
        // 关闭文件，fsync
        fsync(server.repl_transfer_fd);
        close(server.repl_transfer_fd);

        // 重命名临时文件
        rename(server.repl_transfer_tmpfile, server.rdb_filename);

        // 清空当前所有数据
        emptyData(-1, server.repl_empty_db_flags, NULL);

        // 加载 RDB 到内存
        // rdbLoad() 会解析 RDB 文件并填充到 server.db[] 中
        rdbSaveInfo rsi = RDB_SAVE_INFO_INIT;
        retval = rdbLoad(server.rdb_filename, &rsi, 
                         RDBFLAGS_NONE);

        // 从 RDB 中恢复 replid 和 offset
        if (rsi.repl_id_is_set &&
            sdslen(rsi.repl_id) == CONFIG_RUN_ID_SIZE)
        {
            memcpy(server.replid, rsi.repl_id,
                   CONFIG_RUN_ID_SIZE);
        }
        server.master_repl_offset = rsi.repl_offset;

        // 设置复制状态为 CONNECTED
        server.repl_state = REPL_STATE_CONNECTED;
        
        // 注册 I/O 处理器 → 开始接收增量命令
        replicationCreateMasterClient(server.master, -1);
    }
}
```

---

## 四、底层关键数据结构

### 1. 主节点视角的从节点 client

```c
// src/server.h
typedef struct client {
    // ===== 基础连接信息 =====
    uint64_t id;              // 客户端唯一 ID
    connection *conn;         // 网络连接抽象
    int flags;                // CLIENT_SLAVE | CLIENT_MASTER | ...

    // ===== 输入缓冲区 =====
    sds querybuf;             // 输入缓冲区（积累未完整解析的数据）
    size_t qb_pos;            // 已解析位置
    size_t querybuf_peak;     // 缓冲区峰值大小

    // ===== 命令解析结果 =====
    robj **argv;              // 解析后的命令参数数组
    int argc;                 // 参数个数
    struct redisCommand *cmd; // 当前命令指针

    // ===== 输出缓冲区 =====
    // 三种策略：
    // 1. reply buffer (固定缓冲区，写满后溢出到列表)
    // 2. reply list   (动态列表，每个节点是 16KB 字符串)
    // 3. 无缓冲（直写）
    char buf[PROTO_REPLY_CHUNK_BYTES];  // 16KB 固定缓冲区
    int bufpos;                          // 当前写入位置
    list *reply;                         // 溢出的回复链表
    size_t reply_bytes;                  // 总输出字节数

    // ===== 复制相关字段 (从节点在主节点上的表现) =====
    int replstate;            // 从节点的复制状态
    int repldbfd;             // RDB 文件 fd
    off_t repldboff;          // RDB 发送偏移
    off_t repldbsize;         // RDB 总大小
    sds replpreamble;         // RESP 大字符串前缀

    long long reploff;        // 该从节点已确认执行到的 offset
    long long repl_ack_off;   // 最后一次 REPLCONF ACK 报告的 offset
    time_t repl_ack_time;     // 最后收到 ACK 的时间

    // ...
} client;
```

### 2. repl_backlog 结构

```c
// src/server.h
typedef struct redisServer {
    // 复制积压缓冲区
    char *repl_backlog;         // 指向环形缓冲区的指针
    long long repl_backlog_size;    // 缓冲区总大小（字节）
    long long repl_backlog_idx;     // 当前写入下标（环形游标）
    long long repl_backlog_histlen; // 缓冲区中有效数据长度
    long long repl_backlog_off;     // 缓冲区第一条数据的全局 offset
};
```

```
内存布局（size = 16 示例）：

物理地址:  [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [A] [B] [C] [D] [E] [F]
内容:       D   E   F   G   H   I   J   K   L   M   N   O   P   Q   R   S

idx=0 (环形游标指向下一个写入位置)
off=20 (缓冲区起始数据对应全局 offset 20)
histlen=16 (缓冲区满)

全局 offset: 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35
物理地址:     [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [A] [B] [C] [D] [E] [F]
内容:          D   E   F   G   H   I   J   K   L   M   N   O   P   Q   R   S

master_repl_offset = 35

某个从节点请求 offset=28 的数据：
  相对偏移 = 28 - 20 = 8
  起始物理位置 = idx - histlen + 8 = 0 - 16 + 8 = -8
  取模: (-8 + 16) % 16 = 8
  从 [8] 开始读 → "LMNOPQRS" → 8 字节发送给从节点
```

### 3. client 输出缓冲区的三种层次

```c
// src/networking.c — addReply() 系列函数

void addReply(client *c, robj *obj) {
    // 如果有阻塞的写处理器，预安装
    if (prepareClientToWrite(c) != C_OK) return;

    // 序列化对象为 RESP 格式
    if (sdsEncodedObject(obj)) {
        _addReplyProtoToList(c, obj->ptr, sdslen(obj->ptr));
    } else if (obj->encoding == OBJ_ENCODING_INT) {
        // 小整数优化：直接用固定缓冲区
        if (obj->ptr < OBJ_SHARED_BULKHDR_LEN) {
            // 使用共享对象（预分配的 RESP 字符串）
            _addReplyProtoToList(c, 
                shared.bulkhdr[obj->ptr].ptr, ...);
        }
    }
}

// 最底层：写入输出缓冲区
void _addReplyProtoToList(client *c, const char *s, size_t len) {
    // 先尝试写入固定缓冲区 c->buf
    if (c->bufpos + len <= PROTO_REPLY_CHUNK_BYTES) {
        memcpy(c->buf + c->bufpos, s, len);
        c->bufpos += len;
        return;
    }

    // 固定缓冲区放不下 → 溢出到 reply 链表
    // 每个链表节点 16KB
    listNode *ln = listLast(c->reply);
    clientReplyBlock *tail = ln ? listNodeValue(ln) : NULL;

    // 尝试填充最后一个节点的剩余空间
    size_t avail = tail ? (PROTO_REPLY_CHUNK_BYTES - tail->used) : 0;
    if (avail > 0) {
        size_t copy = (avail >= len) ? len : avail;
        memcpy(tail->buf + tail->used, s, copy);
        tail->used += copy;
        s += copy;
        len -= copy;
    }

    // 还有剩余 → 新建链表节点
    while (len > 0) {
        size_t chunk_len = len < PROTO_REPLY_CHUNK_BYTES ? 
                           len : PROTO_REPLY_CHUNK_BYTES;
        clientReplyBlock *buf = zmalloc(
            sizeof(clientReplyBlock) + chunk_len);
        memcpy(buf->buf, s, chunk_len);
        buf->used = chunk_len;
        listAddNodeTail(c->reply, buf);
        c->reply_bytes += chunk_len + 
                          sizeof(clientReplyBlock);
        s += chunk_len;
        len -= chunk_len;
    }
}
```

```
输出缓冲区内存布局：

client 结构体内部：
┌────────────────────────────────────────────────────────┐
│ buf[16384]                    (固定缓冲区 16KB)          │
│ ┌──────────────────────────────────────────────────┐   │
│ │ RESP数据1 │ RESP数据2 │ RESP数据3 │  空闲空间     │   │
│ └──────────────────────────────────────────────────┘   │
│ bufpos → ─────────────────────────────────↑            │
│                                                  16384 │
├────────────────────────────────────────────────────────┤
│ reply (链表) ──→ [节点1:16KB] → [节点2:16KB] → [节点3] │
│                   ↑ 已满               ↑ 已满     ↑部分 │
├────────────────────────────────────────────────────────┤
│ reply_bytes = 所有链表节点的总字节数                      │
│               用于 client-output-buffer-limit 检查       │
└────────────────────────────────────────────────────────┘
```

### 4. 从节点的 output buffer 限制

```c
// src/networking.c
int closeClientOnOutputBufferMemExceeded(client *c) {
    // 检查是否超过 client-output-buffer-limit
    // 对于从节点：hard limit 和 soft limit
    
    // 配置格式：
    // client-output-buffer-limit replica <hard> <soft> <soft_seconds>
    // 例如：client-output-buffer-limit replica 256mb 64mb 60
    
    if (c->flags & CLIENT_SLAVE) {
        // 检查 hard limit
        if (server.client_obuf_limits[CLIENT_TYPE_SLAVE].hard_limit_bytes 
            && c->reply_bytes > 
            server.client_obuf_limits[CLIENT_TYPE_SLAVE].hard_limit_bytes)
        {
            // 强制断开
            freeClient(c);
            return 1;
        }
        
        // 检查 soft limit
        if (server.client_obuf_limits[CLIENT_TYPE_SLAVE].soft_limit_bytes 
            && c->reply_bytes > 
            server.client_obuf_limits[CLIENT_TYPE_SLAVE].soft_limit_bytes)
        {
            time_t elapsed = server.unixtime - c->obuf_soft_limit_reached_time;
            if (elapsed > 
                server.client_obuf_limits[CLIENT_TYPE_SLAVE].soft_limit_seconds)
            {
                // 超过 soft limit 持续时间，断开
                freeClient(c);
                return 1;
            }
        }
    }
    return 0;
}
```

---

## 五、RDB 传输的网络层细节

### 1. 有盘复制的 I/O 路径

```
主节点                                    从节点
  |                                         |
  | 1. fork() 子进程                         |
  |    子进程:                               |
  |    ┌───────────────────────┐             |
  |    │ 遍历内存 → 写 RDB 文件 │             |
  |    │ write(fd, data, len)  │             |
  |    │ → page cache          │             |
  |    │ → 刷盘（可选 fsync）   │             |
  |    └───────────────────────┘             |
  |    子进程退出                              |
  |                                         |
  | 2. 主进程:                               |
  |    open(rdb_filename)                    |
  |    register write handler               |
  |    ↓                                     |
  | 3. event loop 每次迭代:                   |
  |    ┌──────────────────────────────┐      |
  |    │ read(rdb_fd, buf, 16KB)      │      |
  |    │   → page cache → 用户态      │      |
  |    │                              │      |
  |    │ connWrite(socket, buf, n)    │──────│→ TCP send buffer
  |    │   → kernel socket buffer     │      │   → 网卡 → 网络
  |    │                              │      │
  |    │ 如果 socket 缓冲区满 (EAGAIN)│      │
  |    │   → 暂停，等可写事件          │      │
  |    └──────────────────────────────┘      │
  |                                         │
  |                                         │ recv(socket)
  |                                         │ → write(tmp_fd)
  |                                         │ → page cache
  |                                         │ (接收完成后 fsync)
```

**I/O 读写次数分析：**

```
有盘复制的 I/O 路径：

主节点侧：
  子进程写 RDB:  write() × N 次     (内存 → page cache → 磁盘)
  主进程读 RDB:  read()  × M 次     (磁盘 → page cache → 用户态)
  主进程发网络:  send()  × M 次     (用户态 → kernel socket buffer → 网卡)

从节点侧：
  接收 RDB:      recv()  × M 次     (网卡 → kernel buffer → 用户态)
  写临时文件:    write() × M 次     (用户态 → page cache → 磁盘)
  加载 RDB:      read()  × K 次     (磁盘 → page cache → 用户态 → 内存)

总磁盘 I/O: N(写) + M(读) + M(写) + K(读)
            至少 4 次磁盘 I/O 路径
```

### 2. sendBulkToSlave 的网络写入细节

```c
// src/replication.c
void sendBulkToSlave(connection *conn) {
    client *slave = connGetPrivateData(conn);
    char buf[PROTO_IOBUF_LEN];  // 16KB

    // 发送 RESP 前缀 "$<size>\r\n"
    if (slave->replpreamble) {
        nwritten = connWrite(conn, slave->replpreamble,
                            sdslen(slave->replpreamble));
        // connWrite() → 连接抽象层
        //   → connSocketWrite()
        //     → write(fd, buf, len)
        //     → 或 writev(fd, iov, iovcnt) 如果有 iovec
        
        if (nwritten <= 0) {
            if (errno == EAGAIN) {
                // socket 发送缓冲区满了
                // 不做任何事，等下次可写事件
                return;
            }
            // 连接错误
            freeClient(slave);
            return;
        }
        // 部分写：更新 preamble 指针，下次继续
        sdsrange(slave->replpreamble, nwritten, -1);
        if (sdslen(slave->replpreamble) == 0) {
            sdsfree(slave->replpreamble);
            slave->replpreamble = NULL;
        }
        return;
    }

    // 从 RDB 文件读一块数据
    lseek(slave->repldbfd, slave->repldboff, SEEK_SET);
    buflen = read(slave->repldbfd, buf, PROTO_IOBUF_LEN);
    // 可能触发 page cache 命中（子进程刚写过）
    // 或触发磁盘 I/O（数据已被淘汰出 page cache）

    // 写入 socket
    nwritten = connWrite(conn, buf, buflen);
    // → write(fd, buf, buflen)
    // → 内核将数据从用户态拷贝到 socket 发送缓冲区
    // → TCP 协议栈分段、发送
    // → 网卡发出

    if (nwritten <= 0) {
        // EAGAIN 或错误
        return;
    }

    // 部分写处理
    if (nwritten != buflen) {
        // 重新 seek，下次从相同位置继续读
        lseek(slave->repldbfd, 
              slave->repldboff + nwritten, SEEK_SET);
    }

    slave->repldboff += nwritten;
    slave->repl_ack_time = server.unixtime;

    // 检查是否发送完成
    if (slave->repldboff == slave->repldbsize) {
        close(slave->repldbfd);
        slave->repldbfd = -1;

        // RDB 传输完成！
        // 切换到命令传播模式
        slave->replstate = SLAVE_STATE_ONLINE;
        slave->repl_put_online_on_ack = 1;

        // 安装新的写处理器：sendReplyToClient()
        // 用于发送在 RDB 生成期间积累的写命令
        connSetWriteHandler(slave->conn, sendReplyToClient);
    }
}
```

### 3. 网络层的 connWrite() 抽象

```c
// src/connection.h — 统一连接抽象
typedef struct ConnectionType {
    ssize_t (*write)(connection *conn, const void *data, size_t data_len);
    // ...
} ConnectionType;

// src/socket.c — TCP 连接实现
static ssize_t connSocketWrite(connection *conn, 
                                const void *data, size_t data_len) 
{
    ssize_t ret = write(conn->fd, data, data_len);
    if (ret < 0 && errno != EAGAIN) {
        conn->state = CONN_STATE_ERROR;
        conn->last_errno = errno;
    }
    return ret;
}

// 底层系统调用路径：
// write(fd, data, len)
//   → sys_write()
//   → sock_sendmsg()
//   → tcp_sendmsg()
//     → 将用户态数据拷贝到内核 socket 发送缓冲区 (sk_sndbuf)
//     → 如果缓冲区满 → 返回 -EAGAIN
//     → TCP 分段 → IP 分包 → 网卡发送
```

### 4. TCP 发送缓冲区与流控

```
主节点发送 RDB 的流控机制：

用户态                         内核态                    网络
┌──────────┐               ┌──────────────┐           ┌──────┐
│ Redis    │  write()      │ Socket       │  TCP/IP   │      │
│ 进程     │ ──────────→   │ Send Buffer  │ ───────→  │ 从节点│
│          │               │ (sk_sndbuf)  │           │      │
│          │               │ 默认 128KB   │           │      │
│          │               │              │           │      │
│ 16KB/次  │  EAGAIN ←───  │ 缓冲区满     │ ← ACK ──  │      │
│          │               │              │           │      │
│ 暂停     │               │ 发送窗口缩减  │           │      │
│ 等可写   │  EPOLLOUT ←── │ 缓冲区有空间  │           │      │
│          │               └──────────────┘           └──────┘
└──────────┘

关键参数影响传输速度：
  net.core.wmem_max         → socket 发送缓冲区上限
  net.ipv4.tcp_wmem         → TCP 发送缓冲区自动调节范围
  net.core.somaxconn        → 连接队列大小

Redis 配置影响：
  repl-diskless-sync-delay  → 无盘模式下，等待多久才开始发送
  repl-timeout              → 复制超时（如果长时间无数据传输）
```

---

## 六、复制偏移量（Replication Offset）

### 1. 主节点 offset 的产生

```c
// src/replication.c
void feedReplicationBacklog(void *ptr, size_t len) {
    unsigned char *p = (unsigned char *)ptr;

    // 逐字节写入环形缓冲区
    while (len--) {
        server.repl_backlog[server.repl_backlog_idx++] = *p++;
        
        // 环形回绕
        if (server.repl_backlog_idx >= server.repl_backlog_size) {
            server.repl_backlog_idx = 0;
        }
    }

    // ★ 核心：推进全局 offset
    server.master_repl_offset += len;  // len 是命令序列化后的字节数

    // 更新有效数据长度（不能超过缓冲区大小）
    server.repl_backlog_histlen += len;
    if (server.repl_backlog_histlen > server.repl_backlog_size)
        server.repl_backlog_histlen = server.repl_backlog_size;

    // 更新 backlog 起始 offset
    server.repl_backlog_off = server.master_repl_offset 
                            - server.repl_backlog_histlen + 1;
}
```

### 2. 哪些数据计入 offset

```c
// src/replication.c — replicationFeedSlaves()
void replicationFeedSlaves(int dbid, robj **argv, int argc) {
    // ...

    // 1. SELECT 命令（如果需要切换数据库）
    if (server.slaveseldb != dbid) {
        // 构造 "SELECT <dbid>\r\n" 的 RESP 格式
        sds selectcmd = sdscatprintf(sdsempty(), 
            "*2\r\n$6\r\nSELECT\r\n$%d\r\n%s\r\n",
            llbuf_len, llbuf);
        
        // 写入 backlog → offset 增加
        feedReplicationBacklog(selectcmd, sdslen(selectcmd));
        
        server.slaveseldb = dbid;
    }

    // 2. 实际命令
    // 构造 RESP 格式
    sds cmd = catAppendOnlyGenericCommand(sdsempty(), argc, argv);
    
    // 写入 backlog → offset 增加
    feedReplicationBacklog(cmd, sdslen(cmd));
    
    // 3. 推送给在线从节点
    listIter li;
    listRewind(server.slaves, &li);
    while ((ln = listNext(&li))) {
        client *slave = listNodeValue(ln);
        if (slave->replstate == SLAVE_STATE_ONLINE) {
            // 直接追加到从节点的输出缓冲区
            addReplyProto(slave, cmd, sdslen(cmd));
            // 如果是 SELECT 命令也需要发送
            if (server.slaveseldb != dbid) {
                addReplyProto(slave, selectcmd, sdslen(selectcmd));
            }
        }
    }
}
```

### 3. 哪些数据不计入 offset

```
计入 offset 的：                     不计入 offset 的：
────────────────────────────        ───────────────────────────
✓ SET foo bar                       ✗ PING / PONG
✓ DEL key1                          ✗ REPLCONF ACK
✓ SELECT 0                          ✗ AUTH 认证命令
✓ EXPIRE key 100                    ✗ PUBLISH（但会传播到从节点）
✓ LPUSH list a b c                  ✗ DEBUG 命令
✓ 任何会被传播到从节点的写命令         ✗ 读命令（GET/KEYS 等）
                                    ✗ 管理命令（INFO/CONFIG 等）
```

### 4. 从节点侧 offset 的更新

```c
// src/networking.c — 从节点收到主节点数据后

void processInputBuffer(client *c) {
    // c 是主节点在从节点上对应的 client（server.master）
    // c->flags & CLIENT_MASTER

    while (c->qb_pos < sdslen(c->querybuf)) {
        // 判断是否能取出一个完整命令
        if (c->argc == 0) {
            // 解析 RESP 协议头，确定命令参数个数
            // ...
        }

        // 检查是否读取了所有参数
        if (c->argc > 0) {
            // 所有参数都已读取，执行命令
            if (processCommand(c, CMD_CALL_FULL) == C_OK) {
                // 命令执行成功
            }

            // ★ 关键：更新从节点的 offset
            // offset 增加量 = 这条命令在 RESP 流中占的字节数
            // 这个值在 qbuf 中由已消费的字节数决定
            // 不是命令执行的结果大小，而是命令本身的请求大小

            resetClient(c);
        }
    }

    // 推进已消费的 querybuf
    if (c->qb_pos > 0) {
        sdsrange(c->querybuf, c->qb_pos, -1);
        c->qb_pos = 0;
    }
}

// 在命令处理完成后，offset 的更新发生在：
void commandProcessed(client *c) {
    // 对于来自主节点的命令（CLIENT_MASTER）
    // reploff 在 processMultibulkBuffer() 中逐字节推进
    // 每读到一个 RESP 字节，reploff 就 +1
    // 最终 reploff 反映了"已消费了多少字节的复制流"
}
```

```c
// src/networking.c — 解析 RESP 时推进 offset
int processMultibulkBuffer(client *c) {
    // ...

    // 读取参数数据时，每读一个字节，c->reploff++
    // 这确保了 offset 与主节点发送的字节数完全对应

    if (c->qb_pos < sdslen(c->querybuf)) {
        // 读取参数
        // ...
        c->qb_pos += ...;  // 推进读取位置
    }

    return C_OK;
}
```

### 5. REPLCONF ACK 汇报

```c
// src/replication.c — 从节点每秒发送
void replicationSendAck(void) {
    // server.master 是主节点在从节点上的 client 表示
    if (server.master) {
        // server.master->reploff 是从节点已处理到的 offset
        long long offset = server.master->reploff;
        
        // 发送 REPLCONF ACK <offset>
        sds cmd = sdscatprintf(sdsempty(),
            "REPLCONF ACK %lld\r\n", offset);
        
        // 直接写入主节点连接
        if (connWrite(server.master->conn, cmd, sdslen(cmd)) 
            == -1) 
        {
            // 写入失败，可能是网络问题
            // 不会立即断开，由 repl_timeout 控制
        }
        
        sdsfree(cmd);
    }
}

// src/replication.c — 主节点收到 ACK
void replconfCommand(client *c) {
    int j;

    if ((c->argc % 2) == 0) {
        addReplyError(c, "wrong number of arguments "
                        "for REPLCONF");
        return;
    }

    for (j = 1; j < c->argc; j += 2) {
        if (!strcasecmp(c->argv[j]->ptr, "ack")) {
            // REPLCONF ACK <offset>
            long long offset = strtoll(
                c->argv[j+1]->ptr, NULL, 10);

            if (offset > c->repl_ack_off) {
                // 更新该从节点的确认 offset
                c->repl_ack_off = offset;
                c->repl_ack_time = server.unixtime;

                // 触发脚本缓存的传播
                // （Lua 脚本的 effects 也需要同步到从节点）
                replicationScriptCacheTrigger(c);
            }

            // 注意：主节点不回复 ACK 命令
            return;
        }
    }
}
```

### 6. offset 用于判断从节点健康状态

```c
// src/replication.c
void replicationGetInfo(char *buf, size_t buflen) {
    // ...
    listIter li;
    listRewind(server.slaves, &li);
    while ((ln = listNext(&li))) {
        client *slave = listNodeValue(ln);
        
        // 计算从节点的 lag
        // lag = 主节点当前 offset - 从节点确认的 offset
        long long lag = server.master_repl_offset 
                      - slave->repl_ack_off;
        
        // 输出到 INFO replication
        // slave0:ip=1.2.3.4,port=6380,state=online,
        //        offset=12345,lag=100
    }
}
```

---

## 七、主节点写命令 → 从节点（命令传播底层）

### 1. 命令执行的完整链路

```
客户端发送 "SET foo bar"
    │
    ▼
主节点网络层
    │ readQueryFromClient()
    │   → 读取 socket 数据到 c->querybuf
    │   → processInputBuffer(c)
    │     → processCommand(c)
    │
    ▼
命令执行
    │ setCommand()
    │   → dbAdd() / setGenericCommand()
    │   → 修改内存数据
    │
    ▼
传播（propagate）
    │ propagate() 函数
    │
    ├─→ 如果 AOF 开启:
    │   feedAppendOnlyFile()
    │     → 将命令追加到 AOF 缓冲区
    │
    └─→ 如果有从节点:
        replicationFeedSlaves()
          → 将命令追加到 repl_backlog（offset 推进）
          → 将命令追加到每个在线从节点的输出缓冲区
```

```c
// src/server.c — 命令执行后触发传播

void call(client *c, int flags) {
    // ... 执行命令 ...

    // 命令执行完成后，检查是否需要传播
    if (flags & CMD_CALL_PROPAGATE) {
        int propagate_flags = PROPAGATE_NONE;

        // 如果命令修改了数据
        if (c->cmd->flags & CMD_WRITE) {
            propagate_flags |= PROPAGATE_REPL;
        }

        // 如果有 dirty key（被修改的 key）
        if (dirty != server.dirty) {
            // AOF 传播
            if (server.aof_state != AOF_OFF)
                propagate_flags |= PROPAGATE_AOF;
        }

        // 执行传播
        if (propagate_flags != PROPAGATE_NONE) {
            propagate(c->db->id, c->argv, c->argc, 
                      propagate_flags);
        }
    }
}

void propagate(int dbid, robj **argv, int argc, int flags) {
    // AOF 传播
    if (flags & PROPAGATE_AOF) {
        feedAppendOnlyFile(dbid, argv, argc);
    }

    // 复制传播
    if (flags & PROPAGATE_REPL) {
        replicationFeedSlaves(dbid, argv, argc);
    }
}
```

### 2. replicationFeedSlaves 的完整实现

```c
// src/replication.c
void replicationFeedSlaves(int dbid, robj **argv, int argc) {
    // 确保有 backlog
    if (server.repl_backlog == NULL && listLength(server.slaves) == 0)
        return;  // 没有从节点且无 backlog，无需传播

    // 确保 backlog 存在
    if (server.repl_backlog == NULL) {
        createReplicationBacklog();
    }

    // ===== Step 1: 发送 SELECT DB（如果需要） =====
    char llstr[LONG_STR_SIZE];
    if (server.slaveseldb != dbid) {
        // 构造 SELECT 命令的 RESP 格式
        // SELECT 0 → "*2\r\n$6\r\nSELECT\r\n$1\r\n0\r\n"
        sds selectcmd = sdscatprintf(sdsempty(),
            "*2\r\n$6\r\nSELECT\r\n$%d\r\n%s\r\n",
            (int)strlen(llstr), llstr);

        // 写入 backlog
        feedReplicationBacklog(selectcmd, sdslen(selectcmd));

        // 发送给从节点
        listIter li;
        listRewind(server.slaves, &li);
        while ((ln = listNext(&li))) {
            client *slave = listNodeValue(ln);
            if (slave->replstate == SLAVE_STATE_ONLINE)
                addReplyProto(slave, selectcmd, sdslen(selectcmd));
        }

        sdsfree(selectcmd);
        server.slaveseldb = dbid;
    }

    // ===== Step 2: 构造命令的 RESP 格式 =====
    // catAppendOnlyGenericCommand 生成:
    // "*3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"
    sds cmd = catAppendOnlyGenericCommand(sdsempty(), argc, argv);

    // ===== Step 3: 写入 backlog =====
    feedReplicationBacklog(cmd, sdslen(cmd));
    // → 推进 master_repl_offset
    // → 更新环形缓冲区

    // ===== Step 4: 发送给所有在线从节点 =====
    listIter li;
    listRewind(server.slaves, &li);
    while ((ln = listNext(&li))) {
        client *slave = listNodeValue(ln);
        
        // 只发送给已在线的从节点
        // WAIT_BGSAVE_START / WAIT_BGSAVE_END / SEND_BULK 状态的
        // 从节点正在等待或接收 RDB，不需要在这里发送
        // 它们在 RDB 传输完成后，会从 backlog 中获取这段时间的增量数据
        if (slave->replstate == SLAVE_STATE_ONLINE) {
            addReplyProto(slave, cmd, sdslen(cmd));
        }
    }

    sdsfree(cmd);
}
```

### 3. 从节点输出缓冲区的数据流

```
replicationFeedSlaves() 写入从节点的输出缓冲区后：

client->buf (固定 16KB):
┌──────────────────────────────────────────────────────────┐
│ *3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n│*3\r\n...│
│← 一条命令 RESP ─────────────────────────────→│← 下一条→│
└──────────────────────────────────────────────────────────┘
                                                      ↑ bufpos

当 buf 满了之后，溢出到 reply 链表：
reply → [node1: 16KB] → [node2: 16KB] → [node3: 部分]

事件循环中，handleClientsWithPendingWrites() 遍历所有有输出数据的 client，
调用 writeToClient() 将缓冲区数据通过 connWrite() 发送到 socket。
```

```c
// src/networking.c
int writeToClient(client *c, int handler_installed) {
    ssize_t nwritten = 0;
    int totwritten = 0;

    while (clientHasPendingReplies(c)) {
        // 先发送 c->buf 中的数据
        if (c->bufpos > 0) {
            nwritten = connWrite(c->conn, c->buf + c->sentlen,
                                c->bufpos - c->sentlen);
            if (nwritten <= 0) {
                // EAGAIN 或错误
                break;
            }
            c->sentlen += nwritten;
            totwritten += nwritten;

            // buf 发完了
            if ((int)c->sentlen == c->bufpos) {
                c->bufpos = 0;
                c->sentlen = 0;
            }
        }

        // buf 发完了，发送 reply 链表
        if (c->bufpos == 0 && listLength(c->reply) > 0) {
            clientReplyBlock *buf = listNodeValue(
                listFirst(c->reply));
            
            nwritten = connWrite(c->conn, buf->buf + c->sentlen,
                                buf->used - c->sentlen);
            if (nwritten <= 0) break;

            c->sentlen += nwritten;
            totwritten += nwritten;

            if (c->sentlen == buf->used) {
                listDelNode(c->reply, listFirst(c->reply));
                c->sentlen = 0;
                c->reply_bytes -= sizeof(clientReplyBlock) + buf->used;
            }
        }

        // 限制单次写入量，避免长时间占用事件循环
        if (totwritten > NET_MAX_WRITES_PER_EVENT) {
            // 64KB 限制，下次继续
            break;
        }
    }

    // 检查输出缓冲区限制
    if (closeClientOnOutputBufferMemExceeded(c)) return C_ERR;

    // 如果还有数据待发，保持写事件
    // 如果发完了，取消写事件
    if (!clientHasPendingReplies(c)) {
        c->sentlen = 0;
        if (handler_installed) 
            connSetWriteHandler(c->conn, NULL);
    }

    return C_OK;
}
```

---

## 八、命令传播的底层 — 从节点接收并执行

### 1. 从节点收到命令后的处理流程

```c
// src/networking.c — 从节点收到主节点数据
void readQueryFromMaster(connection *conn) {
    client *c = server.master;  // 主节点在从节点上的 client
    int nread;
    int readlen = PROTO_IOBUF_LEN;  // 16KB

    // 读取数据到 querybuf
    nread = connRead(conn, c->querybuf + sdslen(c->querybuf),
                     readlen);

    if (nread <= 0) {
        // 连接断开
        if (nread == 0 || connGetState(conn) != CONN_STATE_CONNECTED) {
            serverLog(LL_NOTICE, "MASTER <-> REPLICA sync: "
                "master lost connection");
            replicationHandleMasterDisconnection();
        }
        return;
    }

    // 更新最后 I/O 时间
    server.stat_net_input_bytes += nread;

    // 处理缓冲区中的命令
    // processInputBuffer() 会解析 RESP 协议并执行命令
    processInputBuffer(c);
}
```

### 2. processInputBuffer 的精简流程

```c
// src/networking.c
void processInputBuffer(client *c) {
    while (c->qb_pos < sdslen(c->querybuf)) {
        // 如果当前没有在解析多条批量
        if (!c->reqtype) {
            if (c->querybuf[c->qb_pos] == '*') {
                c->reqtype = PROTO_REQ_MULTIBULK;
            } else {
                c->reqtype = PROTO_REQ_INLINE;
            }
        }

        // 解析多条批量请求
        if (c->reqtype == PROTO_REQ_MULTIBULK) {
            if (processMultibulkBuffer(c) != C_OK) break;
        } else {
            if (processInlineBuffer(c) != C_OK) break;
        }

        // 命令已完整解析（c->argc > 0 且所有参数就位）
        if (c->argc > 0) {
            // ★ 执行命令
            // 对于从节点上来自主节点的命令：
            //   CMD_CALL_FULL = 执行 + 传播 + 慢日志 + AOF
            //   但传播部分会被过滤（从节点不会再次传播到其他从节点）
            //   除非有 monitor 或 keyspace notification

            if (processCommand(c, CMD_CALL_FULL) == C_OK) {
                // 命令执行成功
            }

            // 重置客户端状态，准备解析下一条命令
            resetClient(c);
        }

        // 如果客户端被释放（命令执行中出错），退出
        if (c->flags & CLIENT_CLOSE_AFTER_REPLY) return;
    }

    // 从 querybuf 中移除已消费的数据
    if (c->qb_pos > 0) {
        sdsrange(c->querybuf, c->qb_pos, -1);
        c->qb_pos = 0;
    }
}
```

### 3. 从节点执行命令的特殊处理

```c
// src/server.c — processCommand()
int processCommand(client *c) {
    // ...

    // ===== 从节点只读限制 =====
    // 如果当前是只读从节点，且不是来自主节点的命令
    if (server.masterhost && server.repl_slave_ro &&
        !(c->flags & CLIENT_MASTER) &&    // 不是主节点发来的
        !(c->flags & CLIENT_MULTI) &&     // 不在事务中
        c->cmd->flags & CMD_WRITE)        // 是写命令
    {
        addReplyError(c, 
            "READONLY You can't write against a read only replica.");
        return C_OK;
    }

    // ===== 主节点发来的写命令直接执行 =====
    // 不检查只读限制（c->flags & CLIENT_MASTER）
    
    // ===== 从节点不执行的命令 =====
    // 不会再次 propagate 到其他从节点（避免环形传播）
    // 但会传播给 MONITOR 客户端

    // 执行命令
    c->cmd->proc(c);

    // ...
}
```

### 4. 从节点不传播的机制

```c
// src/server.c — call()
void call(client *c, int flags) {
    // 执行命令
    c->cmd->proc(c);

    // 传播检查
    if (flags & CMD_CALL_PROPAGATE) {
        // ★ 关键：从节点收到的命令，默认不传播
        // 只有以下情况才会传播：
        // 1. 命令自身要求强制传播（如 EVAL 脚本修改了数据）
        // 2. 命令被 CLIENT_MASTER 标记且不是 AOF 重写场景

        // 来自主节点的命令不会传播到 AOF 或其他从节点
        // 因为它本身就是从主节点传播来的
        if (c->flags & CLIENT_MASTER) {
            // ★ 不传播！
            // 但如果 AOF 开启，且需要记录到 AOF（用于 AOF 重放），
            // 则写入 AOF
            if (server.aof_state != AOF_OFF && 
                server.aof_rewrite_scheduled) 
            {
                // 可能需要写入 AOF
            }
        }
    }
}
```

---

## 九、无盘复制（Diskless Replication）底层细节

### 1. 原理对比

```
有盘复制（Disk-based）：

  fork() → 子进程写 RDB 到磁盘 → 子进程退出 → 主进程读磁盘 → 发送给从节点
  ├── 优点：子进程快速退出，不长时间持有 page table
  ├── 缺点：两次磁盘 I/O（写 + 读），小实例瓶颈在网络不在磁盘
  └── 适合：磁盘快（SSD）、网络慢、从节点多的场景


无盘复制（Diskless）：

  fork() → 子进程通过 pipe 将 RDB 直接写到主进程 → 主进程边收边发给从节点
  ├── 优点：省去两次磁盘 I/O，纯内存 + 网络
  ├── 缺点：子进程长期存活直到发送完成；多个从节点竞争 pipe 带宽
  └── 适合：磁盘慢（HDD）、网络快、从节点少的场景
```

### 2. 无盘复制的 pipe 通信机制

```c
// src/rdb.c — rdbSaveToSlavesSockets()

int rdbSaveToSlavesSockets(rdbSaveInfo *rsi) {
    int pipefds[2];  // 管道：[0]=读端, [1]=写端
    
    // 创建 pipe
    if (pipe(pipefds) == -1) return C_ERR;

    // 创建 epoll 实例用于管理多个从节点 socket
    int rdb_pipe_read = pipefds[0];
    int rdb_pipe_write = pipefds[1];

    // fork 子进程
    server.rdb_child_pid = redisFork(CHILD_TYPE_RDB);
    
    if (server.rdb_child_pid == 0) {
        /* ===== 子进程 ===== */
        closeListeningSockets(0);
        redisSetProcTitle("redis-rdb-to-slaves");

        // 关闭读端
        close(rdb_pipe_read);

        // 初始化 RDB 写入器，写入 pipe 而不是文件
        rio rdb;
        rioInitWithFd(&rdb, rdb_pipe_write);

        // 写 RDB 到 pipe（与写文件的逻辑完全一致）
        rdbSaveRio(&rdb, rsi, RDBFLAGS_NONE);

        // 写入完成，关闭 pipe
        close(rdb_pipe_write);

        exitFromChild(0);
        
    } else if (server.rdb_child_pid > 0) {
        /* ===== 主进程 ===== */
        // 关闭写端
        close(rdb_pipe_write);

        // 保存 pipe 读端 fd
        server.rdb_pipe_read = rdb_pipe_read;
        server.rdb_child_type = RDB_CHILD_TYPE_SOCKET;

        // 注册 pipe 读端的可读事件
        // 当子进程通过 pipe 写入 RDB 数据时，
        // 主进程读取并分发给从节点
        if (aeCreateFileEvent(server.el, rdb_pipe_read,
            AE_READABLE, rdbPipeReadHandler, NULL) == AE_ERR)
        {
            // ...
        }
    }

    return C_OK;
}
```

### 3. rdbPipeReadHandler — 从 pipe 读数据并分发

```c
// src/replication.c — 主进程从 pipe 读 RDB 数据并发送

void rdbPipeReadHandler(struct aeEventLoop *eventLoop, 
                        int fd, void *privdata, int mask) 
{
    // 子进程通过 pipe 发来的 RDB 数据
    // 可能一次只读到部分数据，需要循环读取
    
    int rdb_finished = 0;

    while (1) {
        // 从 pipe 读取数据
        // 注意：不是一次性读完，而是分块读取
        int nread = read(fd, server.rdb_pipe_buff + 
                         server.rdb_pipe_bufflen,
                         PROTO_IOBUF_LEN - server.rdb_pipe_bufflen);

        if (nread == 0) {
            // pipe EOF → 子进程写完了
            rdb_finished = 1;
            break;
        }

        if (nread == -1) {
            if (errno == EAGAIN) {
                // pipe 暂时没有数据
                break;
            }
            // 错误
            serverLog(LL_WARNING, 
                "Read error from RDB pipe: %s", strerror(errno));
            break;
        }

        server.rdb_pipe_bufflen += nread;

        // ★ 将读到的数据分发给所有等待中的从节点
        int still_pending = 0;
        listIter li;
        listRewind(server.slaves, &li);
        while ((ln = listNext(&li))) {
            client *slave = listNodeValue(ln);
            
            if (slave->replstate == SLAVE_STATE_WAIT_BGSAVE_END) {
                // 这个从节点正在等待 RDB 数据

                // 如果还没有发送 RESP 前缀
                if (!slave->repldbfd) {
                    // 发送 "$<size>\r\n"
                    // ...
                }

                // 写入从节点 socket
                ssize_t nwritten = write(slave->fd,
                    server.rdb_pipe_buff, server.rdb_pipe_bufflen);

                if (nwritten == -1) {
                    if (errno == EAGAIN) {
                        // socket 缓冲区满，标记为等待可写
                        nwritten = 0;
                    } else {
                        // 连接错误
                        freeClient(slave);
                        continue;
                    }
                }

                // 记录已发送的字节数
                slave->repldboff += nwritten;
                
                // 如果没有全部写完，标记需要继续发送
                if (nwritten < server.rdb_pipe_bufflen) {
                    still_pending = 1;
                    // 剩余数据会在下次 pipe 可读时一起处理
                }

                // 检查是否全部发送完成
                if (slave->repldboff == slave->repldbsize) {
                    // 该从节点的 RDB 传输完成
                    slave->replstate = SLAVE_STATE_ONLINE;
                }
            }
        }

        // 重置 buffer（所有从节点都写完了才重置）
        if (!still_pending) {
            server.rdb_pipe_bufflen = 0;
        }
    }

    // 如果子进程已退出（pipe EOF）
    if (rdb_finished) {
        // 移除 pipe 的事件监听
        aeDeleteFileEvent(server.el, fd, AE_READABLE);
        close(fd);

        // 处理最后剩余的数据
        // ...
    }
}
```

### 4. 无盘复制的延迟等待机制

```c
// src/replication.c — startBgsaveForReplication()

int startBgsaveForReplication(int mincapa, int mincapa_slave) {
    // ...
    
    if (server.repl_diskless_sync) {
        // ★ 无盘复制模式

        // 检查是否有延迟配置
        if (server.repl_diskless_sync_delay) {
            // 不立即启动 BGSAVE
            // 而是设置一个延迟定时器
            
            serverLog(LL_NOTICE,
                "Delay next BGSAVE for diskless SYNC");
            
            // 标记所有等待中的从节点
            listIter li;
            listRewind(server.slaves, &li);
            while ((ln = listNext(&li))) {
                client *slave = listNodeValue(ln);
                if (slave->replstate == 
                    SLAVE_STATE_WAIT_BGSAVE_START) 
                {
                    // 设置等待标记
                    slave->repl_start_cmd_time_on_master = 
                        server.unixtime;
                }
            }
            
            // 在 replicationCron() 中检查延迟时间
            // 超过后才真正启动 rdbSaveToSlavesSockets()
            return C_OK;
        }
    }
    // ...
}

// src/replication.c — replicationCron() 中的延迟检查
void replicationCron(void) {
    // ...
    
    // 检查无盘复制延迟
    if (server.rdb_child_pid == -1 && 
        server.repl_diskless_sync &&
        server.repl_diskless_sync_delay > 0)
    {
        int at_least_one_slave_waiting = 0;
        listIter li;
        listRewind(server.slaves, &li);
        while ((ln = listNext(&li))) {
            client *slave = listNodeValue(ln);
            if (slave->replstate == SLAVE_STATE_WAIT_BGSAVE_START) {
                at_least_one_slave_waiting = 1;
                break;
            }
        }
        
        if (at_least_one_slave_waiting) {
            time_t elapsed = time(NULL) - 
                server.repl_diskless_sync_last_delay_start;
            
            if (elapsed >= server.repl_diskless_sync_delay) {
                // 延迟时间到！
                // 启动 BGSAVE（无盘模式）
                startBgsaveForReplication(mincapa, 0);
            }
        }
    }
    
    // ...
}
```

### 5. 无盘复制的 I/O 路径对比

```
有盘复制 I/O 路径（数据流经 4 次磁盘）：

  子进程内存 → write() → page cache → fsync → 磁盘扇区
                                                  │
  主进程 read() ← page cache ← 磁盘扇区 ←────────┘
       │
       └→ connWrite() → kernel socket buffer → 网卡 → 从节点

无盘复制 I/O 路径（数据流经 0 次磁盘）：

  子进程内存 → write(pipe) → pipe 内核缓冲区(内存)
                                    │
  主进程 read(pipe) ←──────────────┘
       │
       └→ connWrite() → kernel socket buffer → 网卡 → 从节点

数据路径上的磁盘 I/O 次数：
  有盘: 写1次 + 读1次 = 2次完整磁盘路径
  无盘: 0次
```

### 6. 无盘复制的限制与调优

```
┌─────────────────────────────────────────────────────────────────────┐
│ 约束                          │ 影响                               │
├───────────────────────────────┼─────────────────────────────────────┤
│ 子进程存活时间长               │ fork() 期间 COW 的 page table      │
│  直到所有从节点收到 RDB         │ 拷贝持续占用内存                    │
│                               │ 在写入密集时可能 double 内存         │
├───────────────────────────────┼─────────────────────────────────────┤
│ 多个从节点共享 pipe            │ 如果某个从节点 socket 缓冲区满      │
│                               │ 会阻塞其他从节点的发送              │
│                               │ → 出现 "慢从节点拖累快从节点"       │
├───────────────────────────────┼─────────────────────────────────────┤
│ repl-diskless-sync-delay=5   │ 默认等待 5 秒收集从节点              │
│                               │ 延迟期间新从节点可以加入             │
│                               │ 但如果只有一个从节点，浪费 5 秒      │
├───────────────────────────────┼─────────────────────────────────────┤
│ pipe 缓冲区默认 65536 字节     │ /proc/sys/fs/pipe-max-size         │
│ 子进程写入速度快于主进程       │ pipe 可能被填满                      │
│ 主进程发送速度               │ 子进程的 write(pipe) 被阻塞          │
│ 受网络带宽限制                │ 整个 RDB 生成过程变慢                │
└───────────────────────────────┴─────────────────────────────────────┘

关键配置：
  repl-diskless-sync yes          → 开启无盘复制
  repl-diskless-sync-delay 5     → 等待从节点连接的秒数
  repl-diskless-sync-max-replicas → 考虑从节点数量决定是否用无盘模式
```

---

## 十、全景时间线

```
从节点 REPLICAOF <master> <port> 开始，到数据同步完成的完整时间线：

T+0.000s   从节点执行 REPLICAOF → server.repl_state = CONNECT
T+1.000s   replicationCron() 检测到 → connectWithMaster()
T+1.001s   TCP SYN 发出
T+1.010s   TCP 三次握手完成 → syncWithMaster()
T+1.010s   发送 PING
T+1.020s   收到 PONG
T+1.020s   发送 REPLCONF listening-port 6380
T+1.030s   收到 +OK
T+1.030s   发送 REPLCONF capa eof capa psync2
T+1.040s   收到 +OK
T+1.040s   发送 PSYNC ? -1 (首次)
T+1.050s   主节点判断：全量同步
T+1.050s   主节点回复：+FULLRESYNC 8371b4fb... 123456
T+1.050s   主节点 fork() 子进程 → BGSAVE 开始
T+1.051s   从节点进入 REPL_STATE_TRANSFER
T+1.100s   主节点子进程生成 RDB 完成（假设小数据）
T+1.101s   主进程开始发送 "$<rdb_size>\r\n"
T+1.102s   主进程开始分块发送 RDB 数据 (16KB/块)
T+1.200s   RDB 发送完成
T+1.200s   主节点开始发送 backlog 中缓存的增量命令
T+1.500s   从节点接收完 RDB → 清空数据 → rdbLoad()
T+2.000s   RDB 加载完成 → repl_state = CONNECTED
T+2.000s   注册 readQueryFromMaster → 开始实时接收增量命令
T+2.001s   开始每秒发送 REPLCONF ACK <offset>

        ─── 正常复制阶段 ───

T+10.000s  主节点执行 SET foo bar (30字节 RESP)
T+10.000s  → replicationFeedSlaves()
T+10.000s    → feedReplicationBacklog(): master_repl_offset += 30
T+10.000s    → addReplyProto(slave, "...\r\n"): 写入从节点输出缓冲区
T+10.001s  事件循环 → writeToClient() → connWrite() → send()
T+10.010s  从节点 recv() → readQueryFromMaster() → processInputBuffer()
T+10.010s    → processCommand() → setCommand() → 内存修改
T+10.010s    → server.master->reploff += 30
T+11.000s  从节点 REPLCONF ACK <新offset>
T+11.001s  主节点收到 → slave->repl_ack_off 更新
```

**核心要点总结**：

- **连接建立**：TCP → PING/PONG → AUTH → REPLCONF → PSYNC，状态机驱动
- **PSYNC**：`runid` 匹配身份，`offset` 定位数据位置，三条路径（replid匹配/replid2匹配/全量）
- **全量同步**：fork() + BGSAVE → RDB 网络传输 → 从节点清空加载
- **offset**：按 RESP 序列化字节数计数，backlog 环形缓冲区存储，REPLCONF ACK 汇报
- **命令传播**：propagate() → replicationFeedSlaves() → backlog + 从节点输出缓冲区 → 事件循环写出
- **无盘复制**：pipe 替代磁盘，子进程直写 pipe → 主进程读 pipe → 网络分发，省去磁盘 I/O
