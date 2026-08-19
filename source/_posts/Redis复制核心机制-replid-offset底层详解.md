---
title: Redis 复制核心机制：replid、offset、second_replid_offset 底层详解
date: 2026-09-07 20:45:00
tags:
  - Redis
  - 主从复制
  - replid
  - 底层原理
categories:
  - 缓存架构
---

## 一、三个核心字段的定义

```c
// src/server.h — redisServer 结构体中的关键字段

typedef struct redisServer {
    // ========== 复制身份标识 ==========
    char replid[CONFIG_RUN_ID_SIZE + 1];        // 当前 replid（40字节hex + '\0'）
    char replid2[CONFIG_RUN_ID_SIZE + 1];       // 上一个主节点的 replid
    long long second_replid_offset;              // replid2 对应的有效偏移量起点

    // ========== 复制偏移量 ==========
    long long master_repl_offset;                // 主节点：已产生的复制数据总字节数
                                                 // 从节点：从主节点收到并处理的字节数
    
    // ========== 积压缓冲区 ==========
    char *repl_backlog;                          // 环形缓冲区指针
    long long repl_backlog_size;                 // 缓冲区总大小
    long long repl_backlog_off;                  // 缓冲区中第一条数据的全局 offset
    long long repl_backlog_histlen;              // 缓冲区中有效数据长度
    long long repl_backlog_idx;                  // 缓冲区当前写入位置（环形下标）
    
    // ...
};
```

---

## 二、replid 的生命周期

### 1. 生成时机

```c
// src/server.c — initServer() 启动初始化
void initServer(void) {
    // ...
    getRandomHexChars(server.replid, CONFIG_RUN_ID_SIZE);
    server.replid[CONFIG_RUN_ID_SIZE] = '\0';
    
    // replid2 初始化为空
    memset(server.replid2, '0', CONFIG_RUN_ID_SIZE);
    server.replid2[CONFIG_RUN_ID_SIZE] = '\0';
    server.second_replid_offset = -1;
    // ...
}
```

**replid 是一个 40 字节的随机十六进制字符串**，类似：

```
8371b4fb1155b71f4a04d3e1bc3e18c4a990aeeb
```

### 2. 主节点上 replid 的变化情况

```
正常运行期间：
  replid = "aaa"  ← 启动时生成，终身不变
  replid2 = "0000..."
  second_replid_offset = -1

SLAVEOF NO ONE 执行时（从节点晋升为主节点）：
  replid2 = "aaa"  ← 保存旧的 replid
  second_replid_offset = master_repl_offset + 1
  replid = "bbb"   ← 生成新的随机 replid
```

```c
// src/replication.c
void replicationCommand(client *c) {
    // ...
    if (!strcasecmp(c->argv[1]->ptr,"no") &&
        !strcasecmp(c->argv[2]->ptr,"one"))
    {
        // ...
        changeReplicationId();  // ← 关键函数
        // ...
    }
}

// 生成新 replid，旧 replid 存入 replid2
void changeReplicationId(void) {
    // 将当前 replid 存为 replid2
    memcpy(server.replid2, server.replid, sizeof(server.replid));
    
    // replid2 的有效偏移量起点 = 当前已产生的数据量 + 1
    // 含义：从这个 offset 开始，数据是由新主节点产生的
    server.second_replid_offset = server.master_repl_offset + 1;
    
    // 生成全新的 replid
    getRandomHexChars(server.replid, CONFIG_RUN_ID_SIZE);
    server.replid[CONFIG_RUN_ID_SIZE] = '\0';
    
    // 清空 backlog（可选，取决于是否需要保留旧数据给增量同步）
    if (server.repl_backlog) {
        // 注意：不清空 backlog！
        // backlog 中的数据仍然可以给使用 replid2 的从节点增量同步
    }
}
```

### 3. 从节点上 replid 的来源

```c
// src/replication.c — 收到主节点的 FULLRESYNC 响应时
void readSyncBulkPayload(connection *conn) {
    // ...
    if (server.repl_state == REPL_STATE_TRANSFER) {
        // RDB 加载完成后
        // RDB 头部包含主节点的 replid 和 offset
        
        // 从 RDB 文件中读取
        char replid[CONFIG_RUN_ID_SIZE + 1];
        long long repl_offset;
        // ... 从 RDB 辅助字段中解析 ...
        
        // 从节点复制主节点的 replid
        memcpy(server.replid, replid, sizeof(server.replid));
        
        // 从节点的 offset 从这里开始
        server.master_repl_offset = repl_offset;
    }
}
```

```
从节点的 replid 本质：

从节点的 replid = 它当前跟随的主节点的 replid
  → 这意味着从节点没有"自己的" replid
  → 它借用主节点的 replid 来标识"我跟到了哪里"

例外：SLAVEOF NO ONE 时，从节点生成自己的 replid
```

---

## 三、offset 的底层运作

### 1. 主节点侧：master_repl_offset 的增长

```c
// src/replication.c — 命令传播入口
void replicationFeedSlaves(int dbid, robj **argv, int argc) {
    // ...
    
    // 第一步：将命令序列化为 RESP 协议格式
    // 例如：SET foo bar → "*3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n"
    sds cmd = catAppendOnlyGenericCommand(sdsempty(), argc, argv);
    size_t cmdlen = sdslen(cmd);  // ← 这就是该命令在复制流中占用的字节数
    
    // 第二步：写入复制积压缓冲区
    feedReplicationBacklog(cmd, cmdlen);
    
    // 第三步：推送给所有在线从节点
    listIter li;
    listRewind(server.slaves, &li);
    while ((ln = listNext(&li))) {
        client *slave = listNodeValue(ln);
        if (slave->replstate == SLAVE_STATE_ONLINE)
            addReplyProto(slave, cmd, cmdlen);
    }
    
    sdsfree(cmd);
}

// 写入 backlog 并推进 offset
void feedReplicationBacklog(void *ptr, size_t len) {
    // 遍历写入环形缓冲区
    unsigned char *p = ptr;
    while (len--) {
        server.repl_backlog[server.repl_backlog_idx] = *p++;
        server.repl_backlog_idx++;
        
        // 环形回绕
        if (server.repl_backlog_idx >= server.repl_backlog_size)
            server.repl_backlog_idx = 0;
    }
    
    // 关键：推进全局 offset
    server.master_repl_offset += len;  // ← 每写入 N 字节，offset += N
    
    // 更新有效数据长度
    server.repl_backlog_histlen += len;
    if (server.repl_backlog_histlen > server.repl_backlog_size)
        server.repl_backlog_histlen = server.repl_backlog_size;
    
    // 更新 backlog 的起始 offset
    // 如果数据超过了缓冲区大小，最旧的数据被覆盖
    server.repl_backlog_off = server.master_repl_offset 
                            - server.repl_backlog_histlen + 1;
}
```

### 2. offset 的计数模型

```
假设主节点执行了 3 个命令：

命令1: SET foo bar    → RESP序列化后 14 字节
命令2: DEL key1       → RESP序列化后 10 字节
命令3: INCR counter   → RESP序列化后 16 字节

master_repl_offset 变化：

执行命令前:  offset = 1000
执行命令1后: offset = 1014  (+14)
执行命令2后: offset = 1024  (+10)
执行命令3后: offset = 1040  (+16)

backlog 状态：
backlog_off    = 1000 (第一条命令的起始offset)
histlen        = 40
master_repl_offset = 1040
```

### 3. 从节点侧：接收并推进 offset

```c
// src/replication.c — 从节点读取主节点发来的数据
void readQueryFromMaster(connection *conn) {
    // ...
    nread = connRead(conn, c->querybuf + qblen, readlen);
    
    // 处理接收到的命令（和处理普通客户端命令一样）
    processInputBuffer(c);
    
    // 关键：每处理完一条命令，更新从节点的 offset
    // 注意：这里更新的是 server.master->reploff
    // 也就是从节点汇报给主节点的 offset
}

// 从节点处理完命令后，更新 offset
// 在 processCommand() 执行完后：
void commandProcessed(client *c) {
    // ...
    if (c->flags & CLIENT_MASTER) {
        // 从主节点来的命令
        // reploff 已经在 processInputBuffer 中更新了
        // ... 
    }
}
```

```c
// src/networking.c — 解析 RESP 协议时更新 offset
void processInputBuffer(client *c) {
    while (c->qb_pos < sdslen(c->querybuf)) {
        // ...
        if (processCommand(c, CMD_CALL_FULL) == C_OK) {
            // 从节点收到的命令处理完成后
            // offset 推进
            if (c->flags & CLIENT_MASTER) {
                // 注意：不是在执行时推进，而是在"解析成功"时推进
                // 因为即使命令被拒绝，数据也已经从流中消费了
            }
        }
        
        // 推进 reploff
        // c->reploff += 该命令在 RESP 中的字节数
        sdsrange(c->querybuf, c->qb_pos, -1);
        c->qb_pos = 0;
    }
}
```

```c
// 从节点向主节点汇报 offset 的时机
void replicationCron(void) {
    // ...
    // 每秒向主节点发送 REPLCONF ACK
    if (server.master && 
        server.master->flags & CLIENT_REPLCONF_ACK)
    {
        // 发送当前已处理到的 offset
        long long offset = server.master->reploff;
        sds cmd = sdscatprintf(sdsempty(), 
            "REPLCONF ACK %lld\r\n", offset);
        // ...
    }
}
```

### 4. 主节点收到 ACK 后

```c
// src/replication.c
void replconfCommand(client *c) {
    // ...
    if (!strcasecmp(c->argv[j]->ptr, "ack")) {
        // 收到从节点汇报的 offset
        long long offset = strtoll(c->argv[j+1]->ptr, NULL, 10);
        
        if (offset > c->repl_ack_off) {
            // 更新该从节点的确认 offset
            c->repl_ack_off = offset;
            // 更新最后收到 ACK 的时间
            c->repl_ack_time = server.unixtime;
        }
    }
}
```

---

## 四、repl_backlog 环形缓冲区详解

### 1. 内存布局

```
repl_backlog_size = 16 (假设很小便于演示)

初始状态（刚创建，无数据）：
┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
│   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │   │
└───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
idx=0
off=1
histlen=0

写入 "ABCDEFGH" (8字节) 后：
┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
│ A │ B │ C │ D │ E │ F │ G │ H │   │   │   │   │   │   │   │   │
└───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
idx=8                                         ↑
off=1                                         master_repl_offset=8

再写入 "IJKLMNOP" (8字节)：
┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
│ A │ B │ C │ D │ E │ F │ G │ H │ I │ J │ K │ L │ M │ N │ O │ P │
└───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
idx=0 (回绕!)                                 ↑
off=1                                          master_repl_offset=16

再写入 "1234" (4字节) — 开始覆盖旧数据：
┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
│ 1 │ 2 │ 3 │ 4 │ E │ F │ G │ H │ I │ J │ K │ L │ M │ N │ O │ P │
└───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
  ↑       ↑
  已被覆盖  idx=4
  off=5   (A~D 被 1~4 覆盖)
  histlen=16 (已达上限)
  master_repl_offset=20
```

### 2. 查找某个 offset 的数据

```c
// 从 backlog 中读取从 psync_offset 开始的数据
// masterTryPartialResynchronization() 中调用

long long addReplyReplicationBacklog(client *c, long long offset) {
    // offset 是从节点请求的起始位置
    // 需要在环形缓冲区中定位到该位置
    
    long long j = (offset - server.repl_backlog_off);  // 相对偏移
    
    // 环形索引计算
    // backlog_off 对应的物理位置是：
    //   (server.repl_backlog_idx - server.repl_backlog_histlen + server.repl_backlog_size) % server.repl_backlog_size
    
    // 然后 j 偏移即可
    long long start = server.repl_backlog_idx 
                     - server.repl_backlog_histlen 
                     + j;
    // 取模
    start = ((start % server.repl_backlog_size) + server.repl_backlog_size) 
            % server.repl_backlog_size;
    
    // 将 [start, end) 范围的数据写入从节点的输出缓冲区
    long long thislen = server.repl_backlog_histlen - j;
    
    if (thislen + start > server.repl_backlog_size) {
        // 跨越环形边界，分两段发送
        // 第一段：start → 缓冲区末尾
        addReplyProto(c, server.repl_backlog + start, 
                      server.repl_backlog_size - start);
        // 第二段：缓冲区开头 → 剩余部分
        addReplyProto(c, server.repl_backlog, 
                      thislen - (server.repl_backlog_size - start));
    } else {
        // 不跨越边界，一段发送
        addReplyProto(c, server.repl_backlog + start, thislen);
    }
    
    return server.master_repl_offset;
}
```

### 3. repl_backlog_off 的计算

```c
// repl_backlog_off = backlog 中第一条数据对应的全局 offset

// 推导：
// master_repl_offset  = 已产生的总字节数
// histlen             = backlog 中当前有效字节数
// repl_backlog_off    = master_repl_offset - histlen + 1

// 所以：
// backlog 有效范围 = [repl_backlog_off, master_repl_offset]
// 从节点的 offset 在这个范围内 → 增量同步
// 从节点的 offset < repl_backlog_off → 数据已被覆盖 → 全量同步
```

```
图示：

全局 offset:  0      100     200     300     400
              |       |       |       |       |
              |<====已覆盖===|=========有效数据=====|
              |       |       |       |       |
              |    backlog_off    master_repl_offset
              |       |       |       |       |
              |       |  从节点A(offset=150)   从节点B(offset=350)
              |       |       |       |       |
              |       |  不在范围内 → 全量    在范围内 → 增量
```

---

## 五、second_replid_offset 详解

### 1. 存在意义

```
问题场景：
  主节点 A(replid=aaa) 有从节点 B 和 C
  A 宕机，Sentinel 将 B 提升为新主
  B 执行 SLAVEOF NO ONE → replid 变为 bbb
  C 重连 B，发送 PSYNC aaa <offset>
  B 如何判断是否可以增量同步？

  如果只有 replid：
    aaa ≠ bbb → 不匹配 → 全量同步 ✗

  有了 replid2 + second_replid_offset：
    aaa == replid2 ✓
    且 offset <= second_replid_offset ✓
    → 增量同步 ✓
```

### 2. 赋值时机与值的含义

```c
// src/replication.c
void changeReplicationId(void) {
    // replid2 = 当前的 replid（即旧主的 replid）
    memcpy(server.replid2, server.replid, sizeof(server.replid));
    
    // second_replid_offset = master_repl_offset + 1
    // 含义：从这个 offset 开始，数据属于新 replid 的范畴
    // [1, second_replid_offset - 1] → 属于 replid2（旧身份）
    // [second_replid_offset, +∞)    → 属于 replid （新身份）
    server.second_replid_offset = server.master_repl_offset + 1;
    
    // 生成新 replid
    getRandomHexChars(server.replid, CONFIG_RUN_ID_SIZE);
    server.replid[CONFIG_RUN_ID_SIZE] = '\0';
}
```

### 3. 完整时间线图解

```
Step 1: 主节点 A 正常运行
──────────────────────────────────────────
A: replid = "aaa", master_repl_offset = 10000

B: replid = "aaa", offset = 9800   (从节点B)
C: replid = "aaa", offset = 9500   (从节点C)

backlog:
A 的 backlog 范围 = [8000, 10000]
  │<====旧数据被覆盖====|=========有效数据=========│
  8000                                           10000


Step 2: 主节点 A 宕机，B 被提升为新主
──────────────────────────────────────────
B 执行 SLAVEOF NO ONE：

changeReplicationId() 执行：
  B.replid2               = "aaa"     (保存旧 replid)
  B.second_replid_offset  = 9800 + 1 = 9801  (B 之前的 offset + 1)
  B.replid                = "bbb"     (新生成)

B 当前状态：
  replid   = "bbb"              [9801, +∞) 是 bbb 产生的数据
  replid2  = "aaa"              [1, 9800]  是 aaa 产生的数据
  second_replid_offset = 9801   分界点
  master_repl_offset = 9800

backlog（不清空！）：
  范围 = [7800, 9800]  (假设 B 的 backlog 稍小)
  │<====旧数据被覆盖====|=====有效数据=====│
  7800                                     9800


Step 3: C 重连 B，发起 PSYNC
──────────────────────────────────────────
C 发送: PSYNC "aaa" 9500

B 的判断逻辑：

  // 第一步：检查 replid 是否匹配
  if ("aaa" == "bbb")  →  NO
  
  // 第二步：检查 replid2 是否匹配（PSYNC2 关键）
  if ("aaa" == "aaa")  →  YES ✓
  
  // 第三步：检查 offset 是否在 replid2 有效范围内
  if (9500 <= 9801)    →  YES ✓
  // 含义：9500 < 9801，说明 C 的数据属于"aaa"时代
  // 且 B 的 backlog 中保留了 aaa 时代的数据
  
  // 第四步：检查 offset 是否在 backlog 物理范围内
  if (9500 >= 7800)    →  YES ✓  (backlog 最旧的数据是 offset 7800)
  
  → +CONTINUE 增量同步！
  → 发送 backlog 中 [9500, 9800] 的数据给 C
  → C 获得 300 字节的增量数据
```

### 4. PSYNC 判断的完整源码

```c
// src/replication.c
int masterTryPartialResynchronization(client *c) {
    // 从节点传来的参数
    char *master_replid = c->argv[1]->ptr;
    long long psync_offset = c->argv[2]->ptr;  // 简化
    
    // ===== 路径1：完全匹配当前 replid =====
    if (!strcmp(master_replid, server.replid)) {
        // 检查 offset 是否在 backlog 内
        if (psync_offset >= server.repl_backlog_off &&
            psync_offset <= server.repl_backlog_off + 
                           server.repl_backlog_histlen)
        {
            // 增量同步
            // 只需发送 backlog 中 [psync_offset, master_repl_offset] 的数据
            addReply(c, shared.psynccnt);  // "+CONTINUE\r\n"
            addReplyReplicationBacklog(c, psync_offset);
            return PSYNC_CONTINUE;
        }
        
        // replid 匹配但 offset 不在范围内 → 全量同步
        goto need_full_resync;
    }
    
    // ===== 路径2：匹配 replid2（PSYNC2 核心路径）=====
    if (!strcmp(master_replid, server.replid2)) {
        // 检查1：offset 在 replid2 有效范围内
        //   second_replid_offset 是新 replid 开始的 offset
        //   所以 psync_offset 必须 < second_replid_offset
        if (psync_offset <= server.second_replid_offset) {
            // 检查2：offset 在 backlog 物理范围内
            if (psync_offset >= server.repl_backlog_off &&
                psync_offset <= server.repl_backlog_off +
                               server.repl_backlog_histlen)
            {
                // 增量同步！
                addReply(c, shared.psynccnt);
                addReplyReplicationBacklog(c, psync_offset);
                return PSYNC_CONTINUE;
            }
        }
        // 不在范围内 → 全量同步
        goto need_full_resync;
    }
    
    // ===== 路径3：都不匹配 → 全量同步 =====
need_full_resync:
    // ...
    // 生成新 replid
    memcpy(server.replid2, server.replid, sizeof(server.replid));
    server.second_replid_offset = server.master_repl_offset + 1;
    getRandomHexChars(server.replid, CONFIG_RUN_ID_SIZE);
    
    addReply(c, shared.psynerr);  // "+FULLRESYNC <new_replid> <offset>\r\n"
    
    // 启动 BGSAVE...
    return PSYNC_FULLRESYNC;
}
```

---

## 六、offset 的精细语义

### 1. 从节点的多个 offset 字段

```c
typedef struct client {
    // ... (从节点在主节点上表现为一个 client)
    
    // ===== 以下字段存在于主节点的从节点 client 上 =====
    
    long long reploff;       // 已确认接收并执行到的 offset
                             // 每处理一条完整命令就推进
    
    long long repl_ack_off;  // 从节点通过 REPLCONF ACK 汇报的 offset
                             // 可能略滞后于 reploff（网络延迟）
    
    time_t repl_ack_time;    // 最后一次收到 ACK 的时间
    
    // ===== 以下字段存在于从节点自身 =====
    // 在 server.master client 上：
    // server.master->reploff = 从节点已从主节点收到并处理的 offset
} client;
```

### 2. 命令执行过程中的 offset 推进

```c
// src/networking.c
void processInputBuffer(client *c) {
    while (c->qb_pos < sdslen(c->querybuf)) {
        // ...
        
        // 1. 检查是否是完整的 RESP 命令
        if (c->querybuf[c->qb_pos] == '*') {
            // 解析 RESP 多条命令
            // ...
        }
        
        // 2. 记录命令开始前的 qb_pos
        size_t prev_pos = c->qb_pos;
        
        // 3. 执行命令
        if (processCommand(c, CMD_CALL_FULL) == C_OK) {
            // ...
        }
        
        // 4. 如果是来自主节点的命令（CLIENT_MASTER 标志）
        //    推进 offset
        if (c->flags & CLIENT_MASTER) {
            // reploff 增加 = 该命令在 RESP 流中占的字节数
            // 注意：不是命令执行结果的字节数
            // 而是命令请求本身的字节数
            // 包含 RESP 协议开销（*3\r\n$3\r\nSET\r\n...）
        }
    }
}
```

### 3. offset 精确值的计算

```
假设主节点发送以下 RESP 数据：

*3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n
│                                                    │
│← 这 30 字节就是 offset 要推进的量 →│

其中：
  *3\r\n        → 4 字节 (数组长度标记)
  $3\r\nSET\r\n → 9 字节 (SET 命令)
  $3\r\nfoo\r\n → 9 字节 (key)
  $3\r\nbar\r\n → 9 字节 (value)
  ─────────────────
  合计           31 字节

主节点发给从节点时，会额外添加 SELECT DB 命令（如果需要切换DB）：
  *2\r\n$6\r\nSELECT\r\n$1\r\n0\r\n  → 16 字节

这些都计入复制流，都参与 offset 计算。
```

---

## 七、三个字段的协作关系全景

```
┌─────────────────────────────────────────────────────────────────┐
│                    主节点（或新晋升的主节点）                       │
│                                                                 │
│  replid   = "bbb"  ──── 当前身份                                 │
│  replid2  = "aaa"  ──── 上一个身份（若有）                        │
│  second_replid_offset = 9801 ──── 身份切换的分界点                 │
│  master_repl_offset = 12000 ──── 已产生的总数据量                  │
│                                                                 │
│  backlog:                                                       │
│  ┌─────────────────────────────────────────────┐                │
│  │ off=8000                 off=12000          │                │
│  │ [====aaa时代数据====|==bbb时代数据==]        │                │
│  │                       ↑                    │                │
│  │              second_replid_offset=9801     │                │
│  └─────────────────────────────────────────────┘                │
│                                                                 │
│  PSYNC 判断矩阵：                                                │
│  ┌──────────────┬────────────────┬──────────────────────────┐   │
│  │ 从节点的 replid│ 从节点的 offset│ 结果                     │   │
│  ├──────────────┼────────────────┼──────────────────────────┤   │
│  │ "bbb"        │ 在 backlog 内  │ +CONTINUE 增量同步       │   │
│  │ "bbb"        │ 不在 backlog 内│ +FULLRESYNC 全量同步     │   │
│  │ "aaa"        │ <= 9801 且     │ +CONTINUE 增量同步       │   │
│  │              │ 在 backlog �内  │ (PSYNC2 关键路径)        │   │
│  │ "aaa"        │ > 9801         │ +FULLRESYNC 全量同步     │   │
│  │ "aaa"        │ 不在 backlog 内│ +FULLRESYNC 全量同步     │   │
│  │ "xxx"        │ 任意值         │ +FULLRESYNC 全量同步     │   │
│  └──────────────┴────────────────┴──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 八、多级复制（级联）中的交互

```
Master → Slave1 → Slave2 （级联复制）

Master: replid=aaa, offset=10000

Slave1: 
  replid=aaa, offset=9500
  SLAVEOF NO ONE 执行后：
    replid2=aaa, second_replid_offset=9501
    replid=bbb, master_repl_offset=9500
    
    继续接受写入，offset 增长到 10200
    replid=bbb, master_repl_offset=10200
    backlog=[8500, 10200]

Slave2:
  replid=aaa, offset=9000（跟随 Slave1 时 Slave1 还是 aaa 的从节点）
  
  Slave1 晋升后，Slave2 重连 Slave1，发送 PSYNC aaa 9000
  
  Slave1 的判断：
    "aaa" != "bbb" → replid 不匹配
    "aaa" == "aaa" → replid2 匹配 ✓
    9000 <= 9501   → second_replid_offset 范围内 ✓
    9000 >= 8500   → backlog 物理范围内 ✓
    → +CONTINUE 增量同步
    
    发送 backlog 中 [9000, 10200] 的数据 → 1200 字节
```

---

## 九、RDB 中的持久化

```
重启时如何恢复 replid 和 offset？

写入 RDB 时（rdbSaveInfoAuxFields）：
  在 RDB 文件头部写入：
    repl-id=<replid>
    repl-offset=<master_repl_offset>

从 RDB 加载时（rdbLoadInfoAuxFields）：
  读取 RDB 头部的 repl-id 和 repl-offset
  恢复到 server.replid 和 server.master_repl_offset

注意：replid2 和 second_replid_offset 不会持久化到 RDB！
  原因：replid2 只在 SLAVEOF NO ONE 时有意义
        如果主节点重启，它不应该再用 replid2 去接受增量同步
        （重启后的主节点应该用新的 replid2 来保存当前 replid）
        
  实际上：
  initServer() 后 replid2 = "000...", second_replid_offset = -1
  从 RDB 加载 replid 后：
  changeReplicationId() 不会在启动时调用
  → 所以重启后的主节点没有 replid2 信息
  → 从节点使用旧 replid 连接时，走路径1（replid 匹配）判断
  → 如果 offset 在 backlog 内 → 增量
  → 如果 backlog 被清空/不够大 → 全量
```

```c
// src/server.c — 启动时
void loadDataFromDisk(int rdbflags) {
    // ...
    if (server.aof_state == AOF_OFF) {
        // 从 RDB 加载
        rdbLoad(server.rdb_filename, &rsi, rdbflags);
        // rsi.repl_id     → 恢复到 server.replid
        // rsi.repl_offset → 恢复到 server.master_repl_offset
    }
    
    // replid2 不会被恢复，保持初始值 "000..."
}
```

---

## 十、关键总结

```
replid:
  - 40字节随机hex，标识一个主节点的"数据流身份"
  - 从节点借用主节点的 replid
  - SLAVEOF NO ONE 时生成新 replid

offset (master_repl_offset):
  - 单调递增的字节计数器
  - 每条写命令的 RESP 序列化长度就是增量
  - 不是逻辑命令计数，而是物理字节计数

second_replid_offset:
  - 仅在 SLAVEOF NO ONE 后有意义
  - 标记了 replid → replid2 切换的精确 offset 分界点
  - 使得使用旧 replid 的从节点仍然可以增量同步
  - 不持久化到 RDB

三者配合实现的核心目标：
  在主从拓扑变化时（重启、故障切换、级联复制），最大化增量同步的概率，
  最小化全量同步带来的网络带宽和 CPU（fork）开销。
```
