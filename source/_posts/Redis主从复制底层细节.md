---
title: Redis 主从复制底层细节
date: 2026-09-07 21:00:00
tags:
  - Redis
  - 主从复制
  - PSYNC
categories:
  - 缓存架构
---

## 一、总体架构概览

Redis 主从复制经历了三个大版本演进：

```
Redis 2.8 之前：SYNC（全量同步，无法断点续传）
Redis 2.8 ~ 4.x：PSYNC1（支持部分重同步，基于 offset + repl_backlog）
Redis 5.0+：PSYNC2（支持级联复制、故障转移后的增量同步）
```

---

## 二、连接建立阶段

### 1. 从节点发起连接

从节点执行 `REPLICAOF <masterip> <masterport>` 后，底层流程：

```
从节点                           主节点
  |                                |
  |--- socket connect ------------>|  (TCP 三次握手)
  |                                |
  |--- PING ---------------------->|  (探活 + 验证连接)
  |<-- PONG -----------------------|
  |                                |
  |--- AUTH <password> ----------->|  (若配置了密码)
  |<-- +OK ------------------------|
  |                                |
  |--- REPLCONF listening-port <p>->|  (告知从节点端口，用于 INFO replication)
  |<-- +OK ------------------------|
  |                                |
  |--- REPLCONF capa psync2 ------->|  (5.0+ 声明能力)
  |<-- +OK ------------------------|
  |                                |
  |--- PSYNC <replid> <offset> --->|  (核心：请求同步)
  |<-- +FULLRESYNC <id> <offset> --|  (全量) 或 +CONTINUE (增量)
```



### 2. PSYNC 命令的关键参数

```
PSYNC <runid> <offset>
```

| 参数 | 含义 |
|------|------|
| `runid` | 主节点的运行ID（40字符hex），首次同步传 `?` |
| `offset` | 从节点已确认的复制偏移量，首次同步传 `-1` |

---

## 三、全量同步（Full Resync）

### 1. 触发条件

```
- 从节点首次连接（replid 为 "?"）
- 从节点的 runid 与主节点不一致（主节点重启过或故障切换）
- 从节点的 offset 不在主节点的 repl_backlog 范围内（积压缓冲区溢出）
```



### 2. 主节点侧的执行流程

```
PSYNC 收到后，主节点 fork 子进程生成 RDB：

主进程（父进程）                     BGSAVE 子进程
    |                                    |
    |--- fork() ----------------------->|
    |                                    |
    |  (主进程继续处理写命令)              |  (遍历内存数据写 RDB)
    |  写命令同时写入 repl_backlog_buffer  |
    |  同时缓存在 client->pending_querybuf |
    |                                    |
    |                                RDB 写完，退出
    |                                    |
    |<-- 子进程退出 ---------------------|
    |                                    |
    |  将 RDB 文件发送给从节点             |
    |  再发送缓冲期间积累的写命令          |
```

### 3. 底层关键数据结构

**repl_backlog（复制积压缓冲区）：**

```c
// server.h
typedef struct replBacklogBuffer {
    char *buf;           // 环形缓冲区
    size_t size;         // 总大小（默认 1MB，可通过 repl-backlog-size 配置）
    long long histlen;   // 历史数据总长度
    long long offset;    // 全局复制偏移量（master_repl_offset）
} replBacklogBuffer;
```

这是一个**环形缓冲区**（circular buffer），写满后覆盖旧数据：

```
          master_repl_offset 不断递增
                    |
[--------已覆盖-----|=========有效数据=========|---空闲---]
^                   ^                           ^
被覆盖的旧数据       backlog 的起始 offset         当前写入位置
```

**从节点的 offset 不在有效范围内 → 触发全量同步。**

### 4. RDB 传输的网络层细节

```
主节点：
1. 打开 RDB 临时文件的 fd
2. 注册可读事件到 event loop
3. 每次 event loop 迭代，调用 rioWrite() 读取 RDB 片段
4. 通过 connWrite() 写入 TCP socket
5. 若 socket 缓冲区满（EAGAIN），暂停传输，等可写事件
6. 传输期间，新写命令缓存在从节点的 client 输出缓冲区

从节点：
1. 读取 RDB 数据，写入临时文件
2. 收完后，清空当前所有 DB 数据
3. 加载 RDB 到内存
4. 加载完毕后，通知主节点继续发送缓冲的写命令
```

---

## 四、增量同步（Partial Resync）

### 1. PSYNC1 机制（Redis 2.8 ~ 4.x）

```c
// 核心判断逻辑（伪代码）
int masterTryPartialResynchronization(client *c) {
    long long psync_offset = c->reploff;  // 从节点上报的 offset
    
    // 条件1：repl_backlog 存在
    // 条件2：从节点的 runid 匹配
    // 条件3：offset 在 backlog 的有效范围内
    if (c->replid == server.replid &&
        psync_offset >= server.repl_backlog_off &&
        psync_offset <= server.repl_backlog_off + server.repl_backlog_histlen)
    {
        // 增量同步：只需发送 backlog 中缺失的部分
        sendBulkToSlave(c, psync_offset);
        return C_OK;
    }
    
    // 否则全量同步
    return C_ERR;
}
```

**核心思想**：主节点用一个环形缓冲区记录最近的写命令，从节点断线重连后，只要 offset 还在缓冲区范围内，就只发送差异部分。

### 2. PSYNC2 机制（Redis 5.0+）

解决了 PSYNC1 的核心痛点：**主节点故障切换后，新主节点没有旧主的 replid 和 offset**。

```
PSYNC2 引入了 replid2（上一个主节点的 replid）+ second_replid_offset：

主节点A（replid=aaa）复制到 从节点B 和 从节点C
        ↓ 主节点A故障
从节点B 被提升为新主节点（replid=bbb，但保留 replid2=aaa）
        ↓
从节点C 重连新主B，发送 PSYNC aaa <offset>
新主B 发现 aaa == 自己的 replid2，且 offset 在范围内
        ↓
+CONTINUE → 增量同步！
```

```c
// server.h 中的关键字段
typedef struct redisServer {
    char replid[CONFIG_RUN_ID_SIZE+1];     // 当前 runid
    char replid2[CONFIG_RUN_ID_SIZE+1];    // 上一个主节点的 runid
    long long second_replid_offset;        // 对应的 offset
    // ...
};
```

---

## 五、复制偏移量（Replication Offset）

### 1. 全局计数模型

```
主节点维护 master_repl_offset：每产生 N 字节写命令，就 +N

从节点维护 slave_repl_offset：每从主节点收到并执行 N 字节命令，就 +N

两者之差 = 数据滞后量
```

### 2. 底层传递机制

```
从节点每秒向主节点发送 REPLCONF ACK <offset>

主节点据此：
  - 更新 INFO replication 中的 lag 值
  - 判断从节点是否在 repl_backlog 有效范围内
  - 决定是否需要断开旧从节点（repl-diskless-sync 且从节点太慢时）
```

```c
// replication.c - 从节点定期发送 ACK
void replicationSendAck(void) {
    if (server.master) {
        sds cmd = sdscatprintf(sdsempty(),
            "REPLCONF ACK %lld\r\n", server.master->reploff);
        // 发送给主节点
    }
}
```

---

## 六、命令传播的底层流程

### 1. 主节点写命令 → 从节点

```
客户端发写命令
    ↓
主节点执行命令
    ↓
propagate() 函数
    ↓
调用 replicationFeedSlaves()
    ↓
将命令追加到 repl_backlog_buffer
同时遍历所有 connected slaves，写入每个 slave 的 client->buf
    ↓
事件循环中，handleClientsWithPendingWrites() 将 buf 数据写出
```

```c
void replicationFeedSlaves(int dbid, robj **argv, int argc) {
    // 1. 构造 RESP 协议格式的命令字符串
    sds cmd = catAppendOnlyGenericCommand(sdsempty(), argc, argv);
    
    // 2. 写入 repl_backlog
    feedReplicationBacklog(cmd, sdslen(cmd));
    
    // 3. 遍历所有从节点
    listIter li;
    listRewind(server.slaves, &li);
    while ((ln = listNext(&li))) {
        client *slave = listNodeValue(ln);
        if (slave->replstate == SLAVE_STATE_ONLINE) {
            // 追加到从节点的输出缓冲区
            addReplyString(slave, cmd, sdslen(cmd));
        }
    }
}
```

### 2. 从节点的特殊处理

```c
// 从节点收到主节点的写命令后：
// 1. 不执行过期淘汰逻辑（依赖主节点的 DEL 命令传播）
// 2. 不触发 keyspace notification
// 3. 执行完后更新 slave_repl_offset
// 4. 发布/订阅消息会被转发到从节点

int processCommand(client *c) {
    // ...
    if (server.masterhost && server.repl_slave_ro &&
        !(c->flags & CLIENT_MASTER) &&
        strcasecmp(c->argv[0]->ptr, "info") != 0 &&
        strcasecmp(c->argv[0]->ptr, "replconf") != 0 &&
        strcasecmp(c->argv[0]->ptr, "wait") != 0) {
        addReplyError(c, "READONLY You can't write against a read only replica.");
        return C_OK;
    }
    // ...
}
```

---

## 七、无盘复制（Diskless Replication）

### 配置：`repl-diskless-sync yes`

```
传统模式（Disk-based）：
主节点 fork → 子进程写 RDB 到磁盘 → 主进程读磁盘 → 通过网络发给从节点

无盘模式（Diskless）：
主节点 fork → 子进程直接通过 pipe 将 RDB 写入主进程 → 主进程通过网络直传
```

### 无盘复制的延迟策略

```c
// repl-diskless-sync-delay 控制等待时间（默认5秒）
// 主节点等待一段时间，让更多从节点连接上来，然后同时发送 RDB

void updateSlavesWaitingBgsave(int bgsaveerr, int type) {
    // ...
    if (server.repl_diskless_sync) {
        // 启动一个定时器，等待 repl-diskless-sync-delay 秒
        // 期间收集更多从节点
        // 超时后统一开始发送
    }
}
```

---

## 八、关键配置参数及影响

| 参数 | 默认值 | 作用 |
|------|--------|------|
| `repl-backlog-size` | 1MB | 环形缓冲区大小，越大越不容易触发全量同步 |
| `repl-backlog-ttl` | 3600s | 主节点没有从节点后，backlog 保留时间 |
| `repl-diskless-sync` | no | 是否使用无盘复制 |
| `repl-diskless-sync-delay` | 5s | 无盘复制等待更多从节点的时间 |
| `repl-ping-replica-period` | 10s | 主节点检测从节点存活的间隔 |
| `repl-timeout` | 60s | 复制超时时间 |
| `client-output-buffer-limit replica` | 256MB/64MB/60s | 从节点输出缓冲区限制 |
| `min-replicas-to-write` | 0 | 最少在线从节点数，不满足则主节点拒绝写入 |
| `min-replicas-max-lag` | 10s | 从节点最大允许延迟秒数 |

---

## 九、复制积压缓冲区的计算公式

```
repl_backlog_size = 2 × (写入速率 bytes/sec × 平均断线时长 sec)

例如：
- 写入 QPS = 10000，平均命令大小 = 100 bytes → 写入速率 ≈ 1 MB/s
- 预期断线恢复时间 = 60 秒
- repl_backlog_size = 2 × 1 × 60 = 120 MB
```

---

## 十、完整时间线总结

```
时间线：

T0  从节点执行 REPLICAOF
T1  TCP 连接建立
T2  PSYNC ? -1
T3  主节点判断：全量同步
T4  主节点 fork() 子进程 → BGSAVE
T5  子进程生成 RDB 完成
T6  主节点通过网络发送 RDB 给从节点
T7  期间新的写命令缓存在从节点的 client 输出缓冲区
T8  从节点接收完 RDB，清空数据，加载 RDB
T9  主节点发送缓冲的写命令
T10 同步完成，从节点进入 ONLINE 状态
T11 之后持续增量同步：主节点传播写命令 → 从节点执行
T12 从节点每秒 REPLCONF ACK <offset>
```

核心要点：**repl_backlog 是增量同步的基石，PSYNC2 通过双 replid 解决了故障切换后的增量同步问题。** 生产环境中，合理配置 `repl-backlog-size` 是避免全量同步风暴的关键。
