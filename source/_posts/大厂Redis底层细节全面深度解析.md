---
title: 大厂 Redis 底层细节 — 全面深度解析
date: 2026-09-07 20:15:00
tags:
  - Redis
  - 底层原理
  - SDS
  - 缓存
categories:
  - 缓存架构
---

## 一、核心数据结构源码级剖析

### 1.1 SDS（Simple Dynamic String）

```c
// Redis 不直接用 C 字符串，而是 SDS
// 根据字符串长度选择不同头部结构（节省内存）

// <= 255 字节 → sdshdr8
struct __attribute__ ((__packed__)) sdshdr8 {
    uint8_t len;        // 已使用长度（1字节）
    uint8_t alloc;      // 分配总长度（1字节）
    unsigned char flags; // 类型标志（低3位表示类型，高5位保留）
    char buf[];         // 柔性数组，实际数据
};

// 256 ~ 65535 字节 → sdshdr16
// 65536 ~ 4294967295 → sdshdr32
// 更大 → sdshdr64

// 内存布局：
// ┌──────┬───────┬────────┬───────────────────────────┐
// │ len  │ alloc │ flags  │ buf: 'h','e','l','l','o'  │
// │ 1B   │ 1B    │ 1B     │ ...                      │
// └──────┴───────┴────────┴───────────────────────────┘
//  ↑ flags 低3位 = SDS_TYPE_8 (001)
//  ↑ 总共 3 字节头 + 5字节数据 + 1字节 \0 = 9字节
//  ↑ 而 C 字符串 "hello" 需要至少 8 字节（strlen+指针开销更大）
```



**SDS 相比 C 字符串的优势（面试高频）：**

```
┌─────────────────────┬──────────────────┬──────────────────┐
│ 特性                 │ C 字符串          │ SDS              │
├─────────────────────┼──────────────────┼──────────────────┤
│ 获取长度             │ O(n) strlen      │ O(1) 直接读 len  │
│ 缓冲区溢出           │ 有风险            │ 无（自动扩容）    │
│ 二进制安全           │ 否（\0截断）      │ 是               │
│ 内存预分配           │ 无               │ 有               │
│ 惰性空间释放         │ 无               │ 有               │
│ 兼容部分C字符串函数   │ —                │ 是（末尾保留\0） │
└─────────────────────┴──────────────────┴──────────────────┘
```

```c
// SDS 扩容策略
sds sdsMakeRoomFor(sds s, size_t addlen) {
    size_t newlen = sdslen(s) + addlen;
    
    if (newlen < SDS_MAX_PREALLOC)   // SDS_MAX_PREALLOC = 1MB
        newlen *= 2;                  // 小于1MB：翻倍扩容
    else
        newlen += SDS_MAX_PREALLOC;   // 大于1MB：每次多分配1MB
    
    // 根据 newlen 选择合适的 sdshdr 类型
    // 可能升级：sdshdr8 → sdshdr16 → sdshdr32
    // 重新分配内存
    // 更新 len, alloc, flags
    return newsh;
}

// 惰性释放
// sdsfree() 不立即释放内存，而是通过 sdsclear() 把 len 置0
// 下次写入时复用已分配的空间
```

### 1.2 Dict（字典/哈希表）与渐进式 Rehash

```c
typedef struct dict {
    dictType *type;         // 类型特定函数（hash、keyCompare、valDestructor...）
    void *privdata;         // 私有数据
    dictht ht[2];           // 两张哈希表（rehash时交替使用）
    long rehashidx;         // rehash 进度，-1 表示未在 rehash
    int16_t pauserehash;    // >0 暂停 rehash
} dict;

typedef struct dictht {
    dictEntry **table;      // 哈希桶数组
    unsigned long size;     // 桶数量（总是 2^n）
    unsigned long sizemask; // size - 1（用于位运算取模）
    unsigned long used;     // 已使用的桶数量
} dictht;

typedef struct dictEntry {
    void *key;
    union {
        void *val;
        uint64_t u64;
        int64_t s64;
        double d;
    } v;
    struct dictEntry *next;  // 链地址法解决冲突
} dictEntry;
```

**渐进式 Rehash 全过程：**

```
初始状态（负载因子 = used/size = 4/4 = 1.0，触发扩容）

ht[0].table (size=4):
┌───┬─────────────────────┐
│ 0 │ dictEntry → dictEntry│  → dictEntry
│ 1 │ NULL
│ 2 │ dictEntry
│ 3 │ dictEntry → dictEntry
└───┴─────────────────────┘

ht[1].table (size=8): [未分配]

rehashidx = -1（未开始）

━━━━━━━ 执行 rehashStep() ━━━━━━━

第1步：分配 ht[1].table，大小 = 第一个 >= ht[0].used*2 的 2^n
       rehashidx = 0

ht[0] (size=4):
┌───┬─────────────────────┐
│ 0 │ A → C → F           │ ← 当前处理这个桶
│ 1 │ NULL
│ 2 │ B
│ 3 │ D → E
└───┴─────────────────────┘

ht[1] (size=8):
┌───┬─────────────────────┐
│ 0 │ NULL
│ 1 │ A                   │ ← hash(A) & 7 = 1
│ 2 │ NULL
│ 3 │ C                   │ ← hash(C) & 7 = 3
│ 4 │ NULL
│ 5 │ F                   │ ← hash(F) & 7 = 5
│ 6 │ NULL
│ 7 │ NULL
└───┴─────────────────────┘
rehashidx = 1

第2步：迁移 ht[0] 桶1（NULL桶，直接跳过）
rehashidx = 2

第3步：迁移 ht[0] 桶2
ht[1]:
  桶2: B → ...

第4步：迁移 ht[0] 桶3
ht[1]:
  桶5: F → D
  桶7: E
rehashidx = 4 → 迁移完成

最终：释放 ht[0]，ht[1] → ht[0]，重置 ht[1]
     rehashidx = -1
```

```c
// 渐进式 rehash 的触发时机
// 1. 每次 CRUD 操作时顺便做一步
int dictRehash(dict *d, int n) {
    while (n-- && d->ht[0].used != 0) {
        // 迁移一个非空桶
        dictEntry *he = d->ht[0].table[d->rehashidx];
        while (he) {
            dictEntry *nextHe = he->next;
            // 重新计算 hash，插入 ht[1]
            uint64_t h = dictHashKey(d, he->key) & d->ht[1].sizemask;
            he->next = d->ht[1].table[h];
            d->ht[1].table[h] = he;
            d->ht[0].used--;
            d->ht[1].used++;
            he = nextHe;
        }
        d->ht[0].table[d->rehashidx] = NULL;
        d->rehashidx++;
    }
}

// 2. serverCron 中定时触发（每100ms）
// 毫秒级别完成 100 个桶的迁移
// 如果没有客户端请求，也不至于拖太久

// 3. rehash 期间的查询：同时查两张表
dictEntry *dictFind(dict *d, const void *key) {
    if (dictIsRehashing(d)) dictRehashStep(d);  // 顺便做一步
    
    // 先查 ht[0]
    he = d->ht[0].table[hash & d->ht[0].sizemask];
    // 找到则返回
    
    // 如果正在 rehash，还要查 ht[1]
    if (dictIsRehashing(d)) {
        he = d->ht[1].table[hash & d->ht[1].sizemask];
    }
}
```

**负载因子与强制 rehash：**

```c
// 负载因子 = ht[0].used / ht[0].size

// 扩容条件（满足任一）：
// 1. 没有 BGSAVE/BGREWRITEAOF 时，负载因子 >= 1
// 2. 有 BGSAVE/BGREWRITEAOF 时，负载因子 >= 5
//    （避免 fork 前大量 rehash 导致 COW 复制更多页面）

// 缩容条件：
// 负载因子 < 0.1（10%）
// 缩小到第一个 >= used 的 2^n

// 大厂面试题：为什么BGSAVE时负载因子阈值提高到5？
// 因为 rehash 需要同时维护 ht[0] 和 ht[1]，内存占用接近翻倍
// fork() 时 COW 会复制更多页面，可能导致内存不足
```

### 1.3 整数集合（IntSet）

```c
typedef struct intset {
    uint32_t encoding;   // 编码方式：INTSET_ENC_INT16/32/64
    uint32_t length;     // 元素数量
    int8_t contents[];   // 柔性数组，实际存储整数
} intset;

// INTSET_ENC_INT16 → 每个元素占 2 字节
// INTSET_ENC_INT32 → 每个元素占 4 字节
// INTSET_ENC_INT64 → 每个元素占 8 字节

// contents 是有序数组（二分查找 O(logN)）
// 存储：[1, 5, 10, 15, 20]

// encoding = INTSET_ENC_INT16 时：
// contents 内存布局：
// ┌────┬────┬────┬────┬────┐
// │ 01 │ 05 │ 0A │ 0F │ 14 │  (小端序，每2字节)
// └────┴────┴────┴────┴────┘
```

**编码升级（关键）：**

```c
// 当插入一个超出当前编码范围的整数时，触发升级
// 例：当前 INT16，插入 100000（超出 32767）

intset *intsetUpgradeAndAdd(intset *is, int64_t value) {
    uint8_t curenc = intrev32ifbe(is->encoding);
    uint8_t newenc = _intsetValueEncoding(value);  // 确定新编码
    int length = intrev32ifbe(is->length);
    
    // 判断插入位置（头部还是尾部）
    int prepend = value < 0 ? 1 : 0;
    
    // 扩容：原长度 * 新编码大小 + 新元素
    is = intsetResize(is, length + 1);
    
    // 从后往前逐个升级（避免覆盖）
    // 每个元素从 2 字节扩展到 4 字节
    while (length--)
        _intsetSet(is, length + prepend, _intsetGetEncoded(is, length, curenc));
    
    // 插入新值
    if (prepend)
        _intsetSet(is, 0, value);
    else
        _intsetSet(is, intrev32ifbe(is->length), value);
    
    is->encoding = intrev32ifbe(newenc);
    is->length = intrev32ifbe(intrev32ifbe(is->length) + 1);
    return is;
}

// 注意：只支持升级，不支持降级
// 一旦升级到 INT64，即使删除了大数，也不会降回来
// 这会浪费内存，大厂监控需要注意
```

### 1.4 Listpack（替代 Ziplist）

```
Redis 7.0 全面用 listpack 替代 ziplist
原因：ziplist 有"级联更新"问题，listpack 彻底解决

Listpack 内存布局：
┌──────────────┬──────────────┬──────────────┬──────────────┬──────┐
│ total_bytes  │ num_elements │ entry1       │ entry2       │ END  │
│ (4 bytes)    │ (2 bytes)    │              │              │ 0xFF │
└──────────────┴──────────────┴──────────────┴──────────────┴──────┘

每个 entry 的结构：
┌─────────────────┬──────────────┬──────────────┐
│ encoding+length │ element data │ backlen      │
└─────────────────┴──────────────┴──────────────┘

关键变化：backlen（前一个 entry 的长度，反向存储）

Ziplist entry:
┌──────────┬──────────┬────────────┐
│ prevlen  │ encoding │ data       │
│ (1或5字节)│          │            │
└──────────┴──────────┴────────────┘
↑ prevlen 需要记录"前一个entry的长度"
  当前一个 entry 从 <254B 扩到 >=254B 时
  prevlen 从 1字节变为 5字节
  → 当前 entry 变大 → 触发下一个 entry 的 prevlen 也变化
  → 级联更新 O(N^2)

Listpack entry:
┌──────────┬────────────┬─────────┐
│ encoding │ data       │ backlen │
│ +length  │            │ (自身长度)│
└──────────┴────────────┴─────────┘
↑ backlen 记录的是"当前 entry 自身的长度"（倒序字节存储）
  不依赖前一个 entry 的大小
  → 不存在级联更新！
```

```c
// listpack entry 查找：从头到尾顺序遍历
// 因为每个 entry 的 backlen 告诉了自身的长度
// 可以直接跳到下一个 entry

// backlen 编码方式（变长，倒序存储）：
// 长度值        backlen 字节数    反向存储示例
// 0~127         1字节             0xxxxxxx
// 128~16383     2字节             10xxxxxx xxxxxxxx
// 16384~...     5字节             11111110 xxxxxxxx ...
```

### 1.5 Quicklist（List 的底层实现）

```
Redis List 底层：quicklist = 双向链表，每个节点是一个 listpack

┌─────────────────────────────────────────────────────────┐
│ quicklist                                                │
│                                                          │
│  head                                        tail        │
│  ┌──┐     ┌──┐     ┌──┐     ┌──┐           ┌──┐       │
│  │N1│◄───▶│N2│◄───▶│N3│◄───▶│N4│◄─── ... ──▶│Nn│       │
│  └──┘     └──┘     └──┘     └──┘           └──┘       │
│   │        │        │        │               │         │
│   ▼        ▼        ▼        ▼               ▼         │
│ listpack listpack listpack listpack       listpack      │
│ [a,b,c]  [d,e,f]  [g,h]    [i,j,k,l]     [m]          │
│                                                          │
│ count = 元素总数                                         │
│ len = 节点数                                             │
│ fill = 每个节点最大大小（-2=8KB, -1=4KB, 正数=元素个数） │
│ compress = 两端不压缩的节点数（LZF压缩中间节点）         │
└─────────────────────────────────────────────────────────┘
```

```c
typedef struct quicklist {
    quicklistNode *head;
    quicklistNode *tail;
    unsigned long count;        // 所有元素总数
    unsigned long len;          // quicklistNode 节点数量
    int fill : QL_FILL_BITS;    // 每个节点的容量限制
    unsigned int compress : QL_COMP_BITS; // LZF 压缩深度
} quicklist;

typedef struct quicklistNode {
    struct quicklistNode *prev;
    struct quicklistNode *next;
    unsigned char *entry;       // 指向 listpack 或 LZF 压缩后的数据
    size_t sz;                  // entry 大小
    unsigned int count : 16;    // 元素数量
    unsigned int encoding : 2;  // RAW=1, LZF=2
    unsigned int container : 2; // PLAIN=1, PACKED=2
    // ...
} quicklistNode;

// LZF 压缩（节省内存，但中间节点被压缩）
// quicklistCompress() 在节点被访问时解压，离开后压缩
// compress=1 表示 head/tail 各 1 个节点不压缩，其余压缩
```

### 1.6 跳表（Skiplist）详解

```c
// Redis 跳表 vs 原版跳表的改进：
// 1. 支持重复 score（比较 ele 字段）
// 2. 有 backward 指针（支持反向遍历）
// 3. 有 span 字段（支持计算排名）

typedef struct zskiplistNode {
    sds ele;
    double score;
    struct zskiplistNode *backward;    // 后退指针
    struct zskiplistLevel {
        struct zskiplistNode *forward;
        unsigned long span;            // 跨度
    } level[];                         // 柔性数组
} zskiplistNode;

// span 的作用：计算排名
// ZRANK mykey member → 需要从 head 到 member 的总 span 之和
//
// HEAD ──span=3──▶ A ──span=2──▶ B ──span=1──▶ C
// ZRANK mykey C = 3 + 2 + 1 = 6（排名从0开始则为5）

// 层数生成概率（斐波那契分布）
// P = 0.25，平均每层约 1/(1-P) = 1.33 个节点
// 空间复杂度 O(N * 1/(1-P)) ≈ O(1.33N)
// 比平衡树的 2N 指针省空间
```

---

## 二、Redis 6.0+ 多线程 IO 模型

```
Redis 6.0 引入 IO 多线程，但命令执行仍是单线程

┌─────────────────────────────────────────────────────────────┐
│                     主线程（event loop）                      │
│                                                              │
│  1. accept 新连接，分配 client 对象                            │
│  2. 读取事件触发                                              │
│     ├── 将可读 client 放入 io_threads_list[1..N]              │
│     ├── 启动 IO 线程（或在主线程中轮询）                       │
│     └── IO 线程并发 read + 解析命令（parse）                   │
│  3. 等待所有 IO 线程完成                                      │
│  4. 【单线程】执行所有已解析的命令                              │
│  5. 将可写 client 放入 io_threads_list[1..N]                  │
│  6. IO 线程并发 write 响应数据                                 │
│  7. 回到事件循环                                              │
└─────────────────────────────────────────────────────────────┘
```

```c
// IO 线程核心代码（networking.c）

// 主线程分配 client 给 IO 线程
void handleClientsWithPendingReadsUsingThreads(void) {
    listIter li;
    listRewind(server.clients_pending_read, &li);
    
    int item_id = 0;
    while ((ln = listNext(&li))) {
        client *c = listNodeValue(ln);
        int target_id = item_id % server.io_threads_num;
        listAddNodeTail(io_threads_list[target_id], c);
        item_id++;
    }
    
    // 唤醒 IO 线程
    io_threads_op = IO_THREADS_OP_READ;
    for (int j = 1; j < server.io_threads_num; j++) {
        pthread_mutex_lock(&io_threads_mutex[j]);
        pthread_cond_signal(&io_threads_cond[j]);
        pthread_mutex_unlock(&io_threads_mutex[j]);
    }
    
    // 主线程自己也处理一批
    listIter li_iter;
    listRewind(io_threads_list[0], &li_iter);
    while ((ln = listNext(&li_iter))) {
        readQueryFromClient(ln->value);  // 读取+解析命令
    }
    
    // 等待所有线程完成
    while (1) {
        unsigned long pending = 0;
        for (int j = 1; j < server.io_threads_num; j++)
            pending += listLength(io_threads_list[j]);
        if (pending == 0) break;
    }
    
    // 现在所有命令都已解析到 client->argv 中
    // 主线程逐个执行
    // ... 这部分仍然是单线程！
}

// IO 线程函数
void *IOThreadMain(void *myid) {
    while (1) {
        // 等待主线程唤醒
        pthread_mutex_lock(&io_threads_mutex[id]);
        while (1) {
            uint64_t eventCount = 0;
            memcpy(&eventCount, &io_threads_pending[id], sizeof(eventCount));
            if (eventCount != 0) break;
            pthread_cond_wait(&io_threads_cond[id], &io_threads_mutex[id]);
        }
        pthread_mutex_unlock(&io_threads_mutex[id]);
        
        // 处理分配给自己的 client 列表
        listIter li;
        listRewind(io_threads_list[id], &li);
        while ((ln = listNext(&li))) {
            client *c = listNodeValue(ln);
            if (io_threads_op == IO_THREADS_OP_READ) {
                readQueryFromClient(c->conn);  // 读取+解析
            } else {
                writeToClient(c, 0);            // 写响应
            }
        }
        listEmpty(io_threads_list[id]);
        
        // 通知主线程完成
        atomicSet(io_threads_pending[id], 0);
    }
}
```

```conf
# IO 线程配置
io-threads 4                     # 线程数（建议：CPU核数的一半，最大128）
io-threads-do-reads yes          # 是否对读操作也使用IO线程

# ⚠️ 关键约束：
# - IO 线程只做 read/write，不做命令执行
# - 线程数不宜太多（线程间同步开销）
# - 4~8 线程是最佳实践
# - 适用于高吞吐场景，单个命令复杂时收益不大
```

```
为什么命令执行不做成多线程？

1. 保证原子性：单线程天然无锁，不需要加锁/解锁的开销
2. 避免上下文切换：单线程 CPU cache 友好
3. 事务简化：WATCH/MULTI/EXEC 天然线性化
4. 命令执行不是瓶颈：IO 才是瓶颈（网络+磁盘）
5. 如果单命令复杂（Lua/大key），靠分片解决

IO 线程 vs 命令执行线程 的时间占比（典型场景）：
  IO:       ████████████  (70%)
  执行:     ████           (20%)
  传播:     ██             (10%)
  → 多线程IO能解决主要瓶颈
```

---

## 三、过期键的精细化管理

### 3.1 过期时间存储（全局过期字典）

```c
// 每个 Redis 数据库维护两个字典
typedef struct redisDb {
    dict *dict;         // 主字典：key → value
    dict *expires;      // 过期字典：key → 过期时间（毫秒时间戳）
    // ...
} redisDb;

// SET key value EX 3600 的底层操作：
// 1. dict 中插入 key → value
// 2. expires 中插入 key → (当前时间 + 3600000)ms

// TTL 命令的实现：
long long TTL(redisDb *db, robj *key) {
    long long expire = getExpire(db, key);  // 从 expires 字典查询
    if (expire == -1) return -1;            // 无过期时间
    
    long long ttl = expire - mstime();      // 过期时间 - 当前时间
    if (ttl < 0) ttl = 0;                   // 已过期但还未被清理
    return ttl;
}
```

### 3.2 惰性删除 + 定期删除 详解

```c
// ── 惰性删除 ──
// 每次访问 key 时检查
robj *lookupKeyReadWithFlags(redisDb *db, robj *key, int flags) {
    robj *val;
    
    // 先检查过期
    if (expireIfNeeded(db, key) == 1) {
        // key 已过期，已删除
        if (server.masterhost == NULL) {
            // 主节点：返回 NULL
            return NULL;
        }
        // 从节点：返回 NULL 但不主动删除（等主节点 DEL 命令）
    }
    
    val = lookupKey(db, key);
    if (val == NULL) {
        server.stat_keyspace_misses++;
    } else {
        server.stat_keyspace_hits++;
    }
    return val;
}

// ── 定期删除 ──
// 在 serverCron() 中调用
void activeExpireCycle(int type) {
    // 策略：随机抽样 + 比例判断
    
    // 每次处理的 db 数量
    int dbs_per_call = CRON_DBS_PER_CALL;  // 默认16（全部db）
    if (type == ACTIVE_EXPIRE_CYCLE_FAST)
        dbs_per_call = 1;  // 快速模式只处理1个db
    
    for (int j = 0; j < dbs_per_call; j++) {
        redisDb *db = server.db[current_db % server.dbnum];
        current_db++;
        
        int expired, sampled = 0;
        long long total_expired = 0;
        
        // 每轮最多抽样 20 个 key
        #define ACTIVE_EXPIRE_CYCLE_LOOKUPS_PER_LOOP 20
        // 或根据 active-expire-effort 动态调整
        
        do {
            // 随机从 expires 字典中取 key
            expired = 0;
            sampled = 0;
            
            long long now = mstime();
            
            while (sampled < ACTIVE_EXPIRE_CYCLE_LOOKUPS_PER_LOOP) {
                dictEntry *de = dictGetRandomKey(db->expires);
                if (de == NULL) break;
                
                sampled++;
                long long ttl = dictGetSignedIntegerVal(de) - now;
                
                if (ttl <= 0) {
                    // 已过期，删除
                    // propagateDel(db, dictGetKey(de));
                    deleteExpiredKey(db, dictGetKey(de));
                    expired++;
                    total_expired++;
                }
            }
            
            // 动态调整：如果过期比例 > 25%，继续抽样
            // 否则跳出，避免CPU浪费
        } while (expired > sampled / 4);
    }
}

// 每次 activeExpireCycle 有时间限制
// FAST 模式：最多 1ms
// SLOW 模式：最多 25% 的 CPU 时间
// 在时间限制内反复抽样删除
```

### 3.3 Redis 7.0+ 过期优化

```
Redis 7.0 引入"主动过期"的改进：

1. EXPIRETIME 命令族：
   EXPIRETIME key → 返回绝对过期时间（秒）
   PEXPIRETIME key → 返回绝对过期时间（毫秒）
   避免客户端计算 TTL 的精度问题

2. 过期字典使用 dictType 的 keyCompare 和 hashFunction
   与主字典共享相同的 hash 函数
   减少了一次 hash 计算

3. 过期 key 的删除使用异步释放（lazyfree）
   unlink 而非 del（在后台线程释放大对象）
```

---

## 四、Jemalloc 内存分配器深度剖析

### 4.1 分配层级

```
Jemalloc 内存管理三级结构：

Thread Cache → Arena → Chunk → Page → Region

┌──────────────────────────────────────────────────────────────┐
│                      jemalloc                                │
│                                                              │
│  Thread Cache (每个线程独立，无锁)                             │
│  ┌─────────────────────────────────────┐                    │
│  │ size class:  8B  16B  32B  48B  64B │                    │
│  │ free list:   []  []   []   []   []  │                    │
│  └─────────────────────────────────────┘                    │
│       │ 请求超过 thread cache → 向 Arena 申请                 │
│       ▼                                                      │
│  Arena (多个 Arena 减少锁竞争)                                │
│  ┌─────────────────────────────────────┐                    │
│  │ Bin → Run (连续的 Page，按 size class 组织)                │
│  │ Small: [8B run] [16B run] [32B run]│                    │
│  │ Large: >= page size 的大块分配       │                    │
│  │ Huge:  >= chunk size 的超大块        │                    │
│  └─────────────────────────────────────┘                    │
│       │ Arena 管理的内存不足 → 向 OS 申请 Chunk               │
│       ▼                                                      │
│  Chunk (默认 4MB，通过 mmap 分配)                             │
│  ┌─────────────────────────────────────┐                    │
│  │ Page 0 │ Page 1 │ Page 2 │ ...      │                    │
│  │ 4KB    │ 4KB    │ 4KB    │          │                    │
│  └─────────────────────────────────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Size Class 与内存对齐

```
Jemalloc 的 size class 分布（默认 4 字节对齐，8 字节对齐，逐步增大）：

小对象 (Small):
  8, 16, 32, 48, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 448, 512

中对象 (Large):
  1KB, 1.5KB, 2KB, 3KB, 4KB, 6KB, 8KB, ...

大对象 (Huge):
  4MB chunk 以上

内存浪费率分析：
  申请 65 字节 → 分配 80 字节 → 浪费率 = (80-65)/80 = 18.75%
  申请 100 字节 → 分配 112 字节 → 浪费率 = 10.7%

大厂优化：
  1. 监控 mem_fragmentation_ratio（used_memory / used_memory_rss）
  2. 超过 1.5 考虑开启 activedefrag
  3. 避免大量不同大小的小对象（加剧碎片）
```

### 4.3 碎片产生的根因

```
场景分析：

初始分配：
  Region A [32B]  Region B [64B]  Region C [32B]  Region D [64B]

删除 B 和 D 后：
  Region A [32B]  [FREE 64B]  Region C [32B]  [FREE 64B]

这两个 64B 的空洞不能合并（不在连续地址）
→ mem_fragmentation_ratio 上升
→ used_memory_rss >> used_memory

解决方案：
  1. activedefrag（主动碎片整理）
  2. 重启 Redis（重新加载，内存最紧凑）
  3. 避免频繁创建删除不同大小的 key
```

---

## 五、持久化深度细节

### 5.1 fork() 与 COW 的内核行为

```
Linux fork() 底层实现（基于 Copy-On-Write）：

调用 fork() 时：
1. 创建新的 task_struct（进程描述符）
2. 复制父进程的 mm_struct（内存描述符）
3. 复制父进程的页表（仅复制页表项，不复制物理页）
4. 将所有页面标记为只读（写时触发 COW）

父进程物理内存：
┌─────────────────────────────────────┐
│  Page 0: [数据A]  ← 两进程共享，只读  │
│  Page 1: [数据B]  ← 两进程共享，只读  │
│  Page 2: [数据C]  ← 两进程共享，只读  │
│  Page 3: [数据D]  ← 两进程共享，只读  │
└─────────────────────────────────────┘

父进程执行 SET key value（修改 Page 1）：
1. CPU 写入 Page 1
2. MMU 检测到只读页面的写操作
3. 触发 Page Fault（缺页中断）
4. 内核处理：
   a. 分配新的物理页面 Page 1'
   b. 复制 Page 1 到 Page 1'
   c. 更新父进程页表，指向 Page 1'，标记为可写
   d. 子进程页表不变，仍指向原始 Page 1（只读）

结果：
┌──────────────────┐    ┌──────────────────┐
│ 父进程物理页面     │    │ 子进程物理页面     │
│ Page 0: [共享]    │    │ Page 0: [共享]    │
│ Page 1': [修改]   │    │ Page 1: [原始]    │
│ Page 2: [共享]    │    │ Page 2: [共享]    │
│ Page 3: [共享]    │    │ Page 3: [共享]    │
└──────────────────┘    └──────────────────┘
新增内存：只有 Page 1'（4KB~8KB，取决于页面大小）

⚠️ 最坏情况：父进程写入所有页面
   新增内存 ≈ 父进程内存大小
   + fork() 时的页表复制
   + 内核管理结构
   → 实际需要 2x 内存
```

### 5.2 大厂优化：无盘复制（Diskless Replication）

```conf
repl-diskless-sync yes
repl-diskless-sync-delay 5          # 等待5秒让更多slave连接
repl-diskless-load swap-before-load # 7.0+：从磁盘加载RDB时使用swap
```

```
传统复制（有盘）：
  Master → BGSAVE → 写 RDB 到磁盘 → 读 RDB 从磁盘 → 发送给 Slave
  磁盘IO：写入 + 读取 = 2次完整IO

无盘复制：
  Master → BGSAVE → 直接通过 socket 发送给 Slave
  子进程 fork() 后，通过 pipe 将 RDB 数据传给主进程
  主进程通过 socket 发送给所有 connected 的 slave
  
  ┌────────────┐
  │ 子进程      │──pipe──▶ 主进程 ──socket──▶ Slave1
  │ (生成RDB)   │──pipe──▶ 主进程 ──socket──▶ Slave2
  │             │──pipe──▶ 主进程 ──socket──▶ Slave3
  └────────────┘
  
  优势：不写磁盘，适合 SSD 寿命敏感的场景
  劣势：多个 slave 时网络带宽是瓶颈
```

### 5.3 AOF 缓冲区三级架构

```
客户端命令 → 三级缓冲区 → 磁盘

┌─────────────────────────────────────────────────────────┐
│  Level 1: 客户端输出缓冲区 (client.output_buffer)        │
│          每个客户端独立，存放命令执行结果                   │
│                                                          │
│  Level 2: AOF 缓冲区 (server.aof_buf)                    │
│          全局共享，存放待写入 AOF 文件的命令               │
│          在 beforeSleep() 中调用 write() 写入 OS page cache│
│                                                          │
│  Level 3: OS Page Cache                                   │
│          内核缓冲区，等待 fsync() 刷入磁盘                 │
│                                                          │
│  Level 4: 磁盘（持久化）                                  │
└─────────────────────────────────────────────────────────┘

fsync 策略对比：

appendfsync always:
  每条命令 → write() → fsync()
  最安全：最多丢失1条命令
  最慢：每次 fsync 需要 0.2~2ms（取决于磁盘）

appendfsync everysec:
  每条命令 → write()
  每秒 → fsync()（后台线程执行）
  平衡：最多丢失1秒数据
  ⚠️ 如果 fsync 超过1秒，下一秒的 fsync 会被跳过
     此时最多丢失2秒数据

appendfsync no:
  每条命令 → write()
  由 OS 决定何时 fsync（默认30秒左右）
  最快：但 OS 崩溃时可能丢失30秒数据
```

### 5.4 AOF 重写缓冲区溢出风险

```
⚠️ 生产事故场景：

AOF 重写期间，子进程正在遍历数据库
此时主进程收到大量写入
增量命令写入 aof_rewrite_buf_blocks

如果写入速度 >> 重写速度：
  aof_rewrite_buf_blocks 会持续膨胀
  → 内存占用急剧增加
  → 可能触发 OOM

防护措施：
1. 监控 aof_rewrite_buffer_length
2. 设置 client-output-buffer-limit
3. 写入高峰期避免触发 AOF 重写
4. 设置 auto-aof-rewrite-percentage 和 auto-aof-rewrite-min-size
   合理控制重写频率
```

---

## 六、集群核心机制

### 6.1 Slot 迁移（Resharding）

```
从 Node A 迁移 slot 5000 到 Node B：

步骤1：Node A 标记 slot 5000 为 MIGRATING
       Node B 标记 slot 5000 为 IMPORTING

步骤2：逐个迁移 slot 中的 key
  ┌────────────────────────────────────────────────────┐
  │ MIGRATE NodeB_IP NodeB_PORT key_name 0 5000 COPY   │
  │                                                     │
  │ MIGRATE 底层：                                      │
  │ 1. DUMP key（序列化为 RDB 格式）                    │
  │ 2. RESTORE key（在目标节点反序列化）                 │
  │ 3. 如果非 COPY 模式，删除源节点的 key               │
  │ 4. 整个过程在源节点原子执行（阻塞该 key）            │
  └────────────────────────────────────────────────────┘

步骤3：迁移期间的请求处理

  客户端发命令给 Node A（slot 5000 的 key "foo"）：
  ┌─ key 存在于 A → 正常执行
  └─ key 已迁移到 B → A 返回 -ASK redirect
      │
      ▼
  客户端发送 ASKING 给 B，然后重发命令
  ┌─ B 收到 ASKING 后标记客户端为可访问 IMPORTING slot
  └─ B 正常执行命令

步骤4：所有 key 迁移完成
  CLUSTER SETSLOT 5000 NODE NodeB_ID
  广播所有节点更新 slot 映射

ASK vs MOVED：
┌─────────────────────────────────────────────────────┐
│ ASK：临时重定向（迁移中）                             │
│   客户端下次仍发给原节点                              │
│   客户端必须先发 ASKING 再发命令                      │
│                                                      │
│ MOVED：永久重定向（已完成迁移）                        │
│   客户端更新本地 slot → node 映射表                   │
│   后续直接发给新节点                                  │
└─────────────────────────────────────────────────────┘
```

```c
// 节点处理客户端命令时的 slot 检查
int processCommand(client *c) {
    // ...
    if (server.cluster_enabled) {
        int hashslot = keyHashSlot(c->argv[1]->ptr, sdslen(c->argv[1]->ptr));
        clusterNode *node = getNodeByQuery(c, c->cmd, c->argv, c->argc, &hashslot, &error_code);
        
        if (node != server.cluster->myself) {
            // 当前节点不负责这个 slot
            if (c->cmd->proc == execCommand) {
                // 事务中的命令，直接拒绝
                reject = 1;
            } else if (server.cluster->migrating_slots_to[hashslot] != NULL) {
                // 正在迁移这个 slot
                if (lookupKey(c->db, c->argv[1], LOOKUP_NONE) == NULL) {
                    // key 已不存在（已迁移走）
                    addReplySds(c, sdsnew("-ASK ..."));
                } else {
                    // key 还在本地，正常执行
                }
            } else if (server.cluster->importing_slots_from[hashslot] != NULL) {
                // 正在导入这个 slot
                if (c->flags & CLIENT_ASKING) {
                    // 客户端发了 ASKING，允许执行
                    executeCommand(c);
                } else {
                    // 没有 ASKING，返回 MOVED
                    addReplySds(c, sdsnew("-MOVED ..."));
                }
            } else {
                // 不在迁移/导入，直接 MOVED
                addReplySds(c, sdsnew("-MOVED ..."));
            }
        }
    }
}
```

### 6.2 Cluster 集群选举

```c
// Slave 发起选举
void clusterHandleSlaveFailover(void) {
    // 条件检查
    // 1. 当前节点是 slave
    // 2. master 被标记为 FAIL
    // 3. 数据足够新（replication offset 不能差太多）
    
    // 增加 configEpoch
    server.cluster->failover_auth_epoch = ++server.cluster->currentEpoch;
    
    // 广播 FAILOVER_AUTH_REQUEST 给所有 master
    clusterBroadcastMessage(CLUSTERMSG_TYPE_FAILOVER_AUTH_REQUEST);
}

// Master 收到选举请求后投票
int clusterProcessPacket(clusterMsg *hdr) {
    if (type == CLUSTERMSG_TYPE_FAILOVER_AUTH_REQUEST) {
        // 检查投票条件：
        // 1. 请求的 epoch 必须大于自己见过的最大 epoch
        // 2. 在这个 epoch 中，自己还没有投过票
        // 3. 请求者的 master 必须是 FAIL 状态
        // 4. 请求者的数据不能太旧（replication offset 比较）
        
        if (满足条件) {
            // 投票
            clusterSendFailoverAuth(node);
            server.cluster->last_vote_epoch = server.cluster->currentEpoch;
        }
    }
    
    if (type == CLUSTERMSG_TYPE_FAILOVER_AUTH_ACK) {
        // 收到投票
        sender->failover_auth_count++;
        
        // 检查是否达到多数票
        int needed = (clusterMasters() / 2) + 1;
        if (sender->failover_auth_count >= needed) {
            // 当选！提升为 master
            clusterFailoverReplaceYourMaster();
        }
    }
}
```

```
选举时间线：

t0: Master(M1) 宕机
t1: Slave(S1) 检测到 M1 FAIL（超过 cluster-node-timeout）
t2: S1 增加 currentEpoch，发 AUTH_REQUEST
t3: 所有 Master 收到请求，投票
t4: S1 获得 > N/2 选票，提升为新 Master
t5: S1 广播 PONG（携带新 slot 信息和新 epoch）
t6: 集群更新拓扑

为什么需要多数票？
  防止脑裂：如果网络分区，只有多数派一侧能选举成功
  少数派一侧的 slave 无法获得多数票

脑裂场景：
  [M1, S1, M2] | 网络分区 | [M3, M4, M5]
  S1 无法获得多数票（只有 M2 投票）
  M3/M4/M5 一侧可以选举出 M1 的替代者
  当网络恢复，M1（旧master）变成新master的slave
  分区期间 M1 收到的数据丢失（受 cluster-node-timeout 和 min-replicas-to-write 保护）
```

### 6.3 Gossip 消息与集群心跳

```c
// 每 100ms（clusterCron）执行
void clusterCron(void) {
    // 1. 遍历所有已知节点
    di = dictGetSafeIterator(server.cluster->nodes);
    while ((de = dictNext(di)) != NULL) {
        clusterNode *node = dictGetVal(de);
        
        // 检查心跳超时
        if (node->ping_sent && 
            (now - node->ping_sent) > server.cluster_node_timeout / 2) {
            // 超过 cluster-node-timeout/2 没收到 PONG
            // 重新建立连接并发送 PING
        }
        
        // 标记 PFAIL（主观下线）
        if (node->ping_sent &&
            (now - node->pong_received) > server.cluster_node_timeout) {
            node->flags |= CLUSTER_NODE_PFAIL;
        }
    }
    
    // 2. 选择随机节点发送 PING
    // 遍历所有节点，选择最久没收到 PONG 的
    clusterNode *best = NULL;
    di = dictGetSafeIterator(server.cluster->nodes);
    while ((de = dictNext(di)) != NULL) {
        clusterNode *node = dictGetVal(de);
        if (best == NULL || node->pong_received < best->pong_received) {
            best = node;
        }
    }
    clusterSendPing(best, CLUSTERMSG_TYPE_PING);
    
    // 3. 处理 FAIL 消息（客观下线）
    // 当超过半数 master 标记某节点 PFAIL → 升级为 FAIL
}

// Gossip 消息携带的数据
typedef struct {
    char nodename[CLUSTER_NAMELEN];
    uint32_t ping_sent;
    uint32_t pong_received;
    char ip[NET_IP_STR_LEN];
    uint16_t port;
    uint16_t cport;
    uint16_t flags;
    uint32_t paddr_port;  // ...
} clusterMsgDataGossip;

// 每次 PING/PONG 消息携带：
// 1. 发送方的完整 slots 信息
// 2. 最多 1/10 的其他节点 gossip 信息
// 3. 发送方的 currentEpoch 和 configEpoch
// 4. 如果是 slave，携带 master 的 node ID
```

---

## 七、大厂生产问题与解决方案

### 7.1 BigKey 检测与处理

```bash
# 检测大 key
redis-cli --bigkeys                # 扫描方式，生产安全
redis-cli --memkeys                # 按内存占用排序
redis-cli --scan --pattern "*" | head -1000  # 手动检查

# 精确分析
redis-cli MEMORY USAGE mykey       # 单个 key 的内存占用（字节）
redis-cli OBJECT ENCODING mykey    # 查看底层编码
redis-cli OBJECT FREQ mykey        # LFU 访问频率
```

```
BigKey 危害：

1. 网络阻塞
   一个 100MB 的 string，传输耗时 ≈ 100MB / 1Gbps ≈ 800ms
   这800ms内该客户端的其他命令全部排队

2. 内存不均（集群环境）
   某个 slot 有 1GB 大 key，导致对应节点内存紧张
   其他节点内存空闲

3. 阻塞主线程
   DEL 一个 1000万元素的 list：
   O(N) 释放所有节点，可能阻塞几百毫秒
   → 所有其他客户端请求延迟飙升

4. fork() 耗时增加
   大 key 在 RDB 序列化时耗时更长

5. 过期/淘汰阻塞
   大 key 被淘汰时，DEL 操作阻塞主线程
```

**解决方案：**

```
String 大 key（>10KB）：
  → 拆分为多个小 key：key_0, key_1, key_2...
  → 读取时 MGET key_0 key_1 key_2
  → 删除时用 UNLINK（异步删除）

Hash 大 key（>5000 fields）：
  → 按 hash(key) % N 拆分到 N 个 hash 中
  → 每个 hash 的 field 不变，只是 key 不同

List 大 key（>100万元素）：
  → 按时间窗口拆分：list:202401, list:202402...
  → 或按范围拆分

Set 大 key：
  → sscan 分批处理

ZSet 大 key：
  → zscan 分批处理
  → 按 score 范围拆分

删除大 key（绝对不能直接 DEL）：
  # UNLINK 是 Redis 4.0+ 的异步删除
  UNLINK my_big_key
  
  # 底层实现：
  # 1. 从主字典中删除 entry（O(1)）
  # 2. 将 value 放入 lazyfree 线程的队列
  # 3. lazyfree 后台线程逐步释放内存
  # 不阻塞主线程
```

### 7.2 HotKey 检测与解决

```bash
# Redis 4.0+ 使用 LFU 统计
redis-cli --hotkeys               # 需要配置 maxmemory-policy 为 LFU

# 或使用 MONITOR（生产慎用，性能损耗大）
redis-cli monitor | head -10000 | awk '{print $4}' | sort | uniq -c | sort -rn
```

```
HotKey 场景：

秒杀商品 key: seckill:item:12345
QPS: 50000/s（单个 key）

问题：
  1. 单个 Redis 实例无法承载 50000 QPS
  2. 集群环境下，请求全部打到一个节点
  3. 即使用了读副本，写入仍然是单点

解决方案（由简到复杂）：

1. 本地缓存（最有效）
   ┌──────────┐    ┌──────────┐
   │ App 1    │    │ App 2    │
   │ 本地缓存  │    │ 本地缓存  │
   │ (100ms)  │    │ (100ms)  │
   └────┬─────┘    └────┬─────┘
        │               │
        ▼               ▼
   ┌────────────────────────┐
   │      Redis             │
   └────────────────────────┘
   
   进程内缓存（Caffeine/Guava），TTL=100ms~1s
   99% 请求在本地处理，只有1%到 Redis

2. 读写分离 + 多副本
   读请求分散到多个 replica

3. 本地缓存 + Redis 二级缓存
   读本地缓存 → miss → 读 Redis → miss → 读 DB
   本地缓存用 Caffeine（Window TinyLFU）

4. Key 拆分（写热点分散）
   seckill:item:12345:0
   seckill:item:12345:1
   seckill:item:12345:2
   ...（共 N 个分片）
   读取时随机选一个
   写入时写入所有分片（或写入时轮询）

5. Proxy 层限流
   使用 Twemproxy / Codis / Redis Cluster Proxy
   在 Proxy 层做热点检测和限流
```

### 7.3 缓存穿透、击穿、雪崩

```
┌────────────────────────────────────────────────────────────────┐
│ 缓存穿透                                                       │
│ 请求的数据在缓存和数据库都不存在                                  │
│ 每次请求都穿透缓存打到数据库                                     │
│                                                                 │
│ 解决方案：                                                      │
│ 1. 布隆过滤器（Bloom Filter）                                   │
│    ┌──────────────────────────────────────────┐                │
│    │ 请求 → BloomFilter 检查 key 是否存在       │                │
│    │   ├─ 不存在 → 直接返回（100% 拦截不存在的） │                │
│    │   └─ 可能存在 → 查缓存 → 查DB              │                │
│    │                                            │                │
│    │ Redis 原生支持：BF.ADD / BF.EXISTS          │                │
│    │ RedisBloom 模块                            │                │
│    └──────────────────────────────────────────┘                │
│                                                                 │
│ 2. 缓存空值                                                     │
│    SET key:不存在 → "" EX 60                                    │
│    后续请求命中缓存，返回空                                      │
│    问题：内存浪费，且DB有了数据后缓存不一致                       │
│                                                                 │
│ 3. 接口层校验                                                    │
│    参数合法性检查，恶意请求直接拦截                               │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ 缓存击穿                                                       │
│ 某个热点 key 过期瞬间，大量并发请求同时打到 DB                    │
│                                                                 │
│ 场景：首页 banner 数据，缓存过期时间 1 小时                       │
│       过期瞬间 10000 个并发请求                                  │
│                                                                 │
│ 解决方案：                                                      │
│ 1. 互斥锁（分布式锁）                                           │
│    SETNX lock:key 1 EX 10                                       │
│    ├─ 成功 → 查DB → 写缓存 → 释放锁                             │
│    └─ 失败 → sleep 50ms → 重试读缓存                            │
│                                                                 │
│ 2. 逻辑过期（不设物理TTL）                                       │
│    value = {data: "xxx", expire: "2024-01-01 12:00:00"}         │
│    读取时判断逻辑过期：                                          │
│    ├─ 未过期 → 返回数据                                         │
│    └─ 已过期 → 异步更新数据 → 先返回旧数据                       │
│    问题：会短暂返回脏数据                                        │
│                                                                 │
│ 3. 热点 key 永不过期                                             │
│    不设 TTL，通过定时任务主动刷新                                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ 缓存雪崩                                                       │
│ 大量 key 在同一时间过期，或 Redis 实例宕机                       │
│ 大量请求直接打到 DB                                              │
│                                                                 │
│ 场景1：批量加载数据，都设了相同的 TTL                             │
│ 场景2：Redis 主节点宕机，故障转移期间所有请求打到 DB              │
│                                                                 │
│ 解决方案：                                                      │
│ 1. TTL 加随机偏移                                                │
│    base_ttl = 3600                                              │
│    actual_ttl = base_ttl + random(0, 300)                       │
│    → 过期时间分散在 3600~3900 秒之间                             │
│                                                                 │
│ 2. 多级缓存                                                    │
│    L1(本地) → L2(Redis) → L3(DB)                               │
│    任一层故障，上层兜底                                          │
│                                                                 │
│ 3. 限流降级                                                    │
│    Redis 不可用时，限制访问 DB 的 QPS                            │
│    超出部分直接返回默认值或错误                                   │
│                                                                 │
│ 4. Redis 高可用                                                │
│    Sentinel 自动故障转移（秒级）                                 │
│    Cluster 多主分片                                             │
└────────────────────────────────────────────────────────────────┘
```

### 7.4 大厂分布式锁

```lua
-- 加锁 Lua 脚本（原子操作）
-- KEYS[1] = lock_key
-- ARGV[1] = unique_id (UUID + thread_id)
-- ARGV[2] = expire_ms

if redis.call('SET', KEYS[1], ARGV[1], 'NX', 'PX', ARGV[2]) then
    return 1
end
return 0

-- 释放锁 Lua 脚本（原子操作：先判断持有者再删除）
-- 防止误删别人的锁
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0

-- 续期锁 Lua 脚本（Watch Dog 机制）
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('PEXPIRE', KEYS[1], ARGV[2])
end
return 0
```

```java
// Redisson 的 Watch Dog 机制（大厂常用）
// 每隔 lockWatchdogTimeout/3 自动续期

/*
 * 加锁流程（Redisson）：
 * 1. 尝试加锁，TTL = 30s（默认）
 * 2. 加锁成功后，启动 WatchDog 定时任务
 * 3. 每 10s（30s/3）续期一次，重置 TTL 为 30s
 * 4. 业务完成，手动释放锁
 * 5. WatchDog 随锁释放而停止
 *
 * Redisson 的可重入锁 Lua 脒本：
 *
 * -- 加锁
 * if (redis.call('exists', KEYS[1]) == 0) then
 *     redis.call('hincrby', KEYS[1], ARGV[2], 1);
 *     redis.call('pexpire', KEYS[1], ARGV[1]);
 *     return nil;
 * end;
 * if (redis.call('hexists', KEYS[1], ARGV[2]) == 1) then
 *     redis.call('hincrby', KEYS[1], ARGV[2], 1);
 *     redis.call('pexpire', KEYS[1], ARGV[1]);
 *     return nil;
 * end;
 * return redis.call('pttl', KEYS[1]);
 *
 * lock_key 的 value 是 Hash 结构：
 * {
 *   "客户端UUID:线程ID": 重入次数
 * }
 */
```

```
分布式锁的问题与 Redlock 算法：

单节点分布式锁的风险：
  Master 加锁成功 → Master 宕机（锁未同步到 Slave）
  → Slave 提升为 Master → 另一个客户端也加锁成功
  → 两个客户端同时持有锁！（违反互斥性）

Redlock 算法（Redisson 默认实现）：
  ┌─────────────────────────────────────────────────┐
  │ 5 个独立的 Redis 实例（非集群，独立部署）           │
  │                                                  │
  │ 1. 获取当前时间 T1                                │
  │ 2. 依次向 5 个实例加锁（相同 key、value、TTL）    │
  │ 3. 计算加锁耗时 T2 - T1                          │
  │ 4. 如果在 > N/2（3个）实例上加锁成功              │
  │    且 总耗时 < TTL                                │
  │    → 加锁成功，有效时间 = TTL - (T2 - T1)        │
  │ 5. 如果加锁失败，向所有实例发送释放锁请求          │
  └─────────────────────────────────────────────────┘

争议（Martin Kleppmann vs Antirez）：
  - 时钟跳跃可能破坏安全性
  - GC 暂停可能导致锁过期但客户端不知道
  - 实际生产中单节点 + Lua 原子操作已足够满足大多数场景
  - 真正强一致的需求应该用 ZooKeeper 或 etcd
```

---

## 八、Pub/Sub 与 Stream

### 8.1 Pub/Sub 底层实现

```c
// 频道订阅：使用字典
typedef struct redisDb {
    dict *pubsub_channels;  // channel_name → list of clients
    dict *pubsub_patterns;  // pattern → list of clients
} redisDb;

// PUBLISH channel message 的实现
int pubsubPublishMessage(robj *channel, robj *message) {
    int receivers = 0;
    
    // 1. 精确匹配频道
    dictEntry *de = dictFind(server.db->pubsub_channels, channel);
    if (de) {
        list *list = dictGetVal(de);
        listIter li;
        listRewind(list, &li);
        while ((ln = listNext(&li))) {
            client *c = listNodeValue(ln);
            addReply(c, ...);  // 直接写入客户端输出缓冲区
            receivers++;
        }
    }
    
    // 2. 模式匹配（遍历所有 pattern）
    dictIterator *di = dictGetIterator(server.db->pubsub_patterns);
    while ((de = dictNext(di))) {
        robj *pattern = dictGetKey(de);
        if (stringmatchlen(pattern->ptr, ...)) {
            // 匹配成功，发送给客户端
            receivers++;
        }
    }
    
    return receivers;
}

// Pub/Sub 的问题（大厂面试常问）：
// 1. 消息不持久化：离线消息丢失
// 2. 不支持消费者组：每条消息广播给所有订阅者
// 3. 消息堆积可能导致输出缓冲区溢出
// → 大厂生产环境推荐用 Kafka/RocketMQ 替代
// → Redis Pub/Sub 只适合实时通知场景
```

### 8.2 Stream（Redis 5.0+，消息队列）

```c
// Stream 底层结构：Radix Tree + Listpack

// ┌─────────────────────────────────────────────────────┐
// │ Stream                                              │
// │                                                     │
// │ Radix Tree (紧凑前缀树)                              │
// │                                                     │
// │  root                                              │
// │  ├─ "1688" → Listpack (存放 ID 以 1688 开头的条目)   │
// │  │  ├── [1688000000000-0, field1, val1, ...]       │
// │  │  ├── [1688000000001-0, field2, val2, ...]       │
// │  │  └── [END]                                      │
// │  ├─ "1689" → Listpack                              │
// │  │  ├── [1689000000000-0, ...]                     │
// │  │  └── [END]                                      │
// │  └─ ...                                            │
// │                                                     │
// │ Consumer Groups:                                    │
// │  group1: {last_delivered_id, PEL[]}                 │
// │  group2: {last_delivered_id, PEL[]}                 │
// └─────────────────────────────────────────────────────┘

// Stream ID: <ms_timestamp>-<sequence>
// 例: 1688000000000-0

typedef struct stream {
    rax *rax;               // Radix Tree，存储所有消息
    uint64_t length;        // 消息总数
    streamID last_id;       // 最后一条消息的 ID
    streamID first_id;      // 第一条消息的 ID
    uint64_t entries_added; // 累计添加的消息数（用于 CG 初始化）
    // ...
} stream;

typedef struct streamConsumerGroup {
    streamID last_id;       // 最后分配给消费者的消息 ID
    rax *pel;               // Pending Entries List（已分配未确认）
    rax *consumers;         // 消费者字典
} streamConsumerGroup;

typedef struct streamConsumer {
    sds name;
    rax *pel;               // 该消费者的未确认消息
    mstime_t active_time;   // 最后活跃时间
} streamConsumer;

// PEL (Pending Entries List) 的作用：
// 消息被 XREADGROUP 分配后，进入 PEL
// 消费者处理完成后 XACK，从 PEL 中移除
// 如果消费者宕机，PEL 中的消息可以被其他消费者 XCLAIM
```

```bash
# 生产环境 Stream 使用

# 创建消费者组
XGROUP CREATE mystream mygroup $ MKSTREAM

# 生产者
XADD mystream * field1 value1 field2 value2

# 消费者（阻塞读取，永不超时）
XREADGROUP GROUP mygroup consumer1 COUNT 10 BLOCK 0 STREAMS mystream >

# 确认消息
XACK mystream mygroup 1688000000000-0

# 处理宕机消费者的消息（认领）
XCLAIM mystream mygroup consumer2 3600000 1688000000000-0

# 查看 pending 消息
XPENDING mystream mygroup - + 10

# 自动裁剪（限制最大长度）
XADD mystream MAXLEN ~ 1000000 * field1 value1
# ~ 表示近似裁剪（实际裁剪到 2^n 边界，效率更高）
# 精确裁剪用 XTRIM
```

---

## 九、Lua 脚本与 Redis Function

### 9.1 Lua 脚本执行引擎

```c
// Redis 嵌入了完整的 Lua 5.1 解释器
// 每个 Redis 实例维护一个共享的 Lua 虚拟机

lua_State *lua;  // 全局 Lua VM

// 执行 EVAL
void evalGenericCommand(client *c, int evalsha) {
    // 1. 查找脚本（SHA1 校验）
    // 2. 如果不存在，编译脚本
    // 3. 设置 Lua 环境（注入 redis.call 等函数）
    // 4. 执行脚本
    // 5. 将 Lua 结果转换为 Redis RESP 格式返回
    
    // 关键：Lua 脚本执行期间，Redis 完全阻塞！
    // 所有其他客户端请求都排队等待
    
    lua_pcall(lua, ...);  // 执行 Lua 函数
}
```

```lua
-- Redis 7.0+ Function（替代 EVAL）
-- 注册持久化的函数库

#!lua name=mylib

-- 原子递增并检查阈值
local function atomic_increment_and_check(keys, args)
    local current = redis.call('INCR', keys[1])
    if current > tonumber(args[1]) then
        redis.call('DEL', keys[1])
        return 0  -- 超过阈值，重置
    end
    return current
end

redis.register_function('rate_limit', atomic_increment_and_check)

-- 调用
-- FCALL rate_limit 1 mykey 100
```

```conf
# Lua 脚本相关配置
lua-time-limit 5000               # 超过5秒记录日志
lua-replicate-commands yes         # Lua中的写命令是否传播到AOF/replica

# Script effects replication（Redis 7.0+）
# Lua 脚本中的 redis.call() 产生的写命令直接传播
# 而不是传播整个 Lua 脚本
# 避免了不确定性函数导致的主从不一致
```

### 9.2 Lua 脚本的 Caching 机制（Redis 7.0+）

```
Redis 7.0 引入 Function Script Cache：

┌──────────────────────────────────────────────────────┐
│  EVAL "return 1" 0                                    │
│  1. 计算 SHA1: "a]b1c2d3..."                          │
│  2. 检查 script cache 中是否存在                       │
│  3. 不存在 → 编译 → 存入 cache                        │
│  4. 后续 EVALSHA 直接命中 cache，跳过编译              │
│                                                      │
│  EVALSHA "a1b1c2d3..." 0                              │
│  → 直接从 cache 获取编译后的函数，执行                 │
│                                                      │
│  AOF/Replica：只记录 EVALSHA（不记录 EVAL）           │
│  节省网络和磁盘空间                                   │
└──────────────────────────────────────────────────────┘
```

---

## 十、大厂 Redis 架构方案

### 10.1 分层缓存架构

```
请求流程：

Client
  │
  ▼
L1: 进程内缓存 (Caffeine, 1~10ms, 容量小)
  │ miss
  ▼
L2: 本地 Redis (同机房, 0.1~0.5ms)
  │ miss
  ▼
L3: 集群 Redis (跨机房, 0.5~2ms)
  │ miss
  ▼
L4: DB (MySQL/PostgreSQL, 5~50ms)
  │
  ▼
回填：DB → L3 → L2 → L1

各层容量：
L1: 1万~10万 key (进程内存 100MB~1GB)
L2: 100万~1000万 key (Redis 实例 10~100GB)
L3: 1亿+ key (Redis Cluster 100GB~10TB)
```

### 10.2 多数据中心 Redis 部署

```
              ┌─────────────────────────┐
              │       全局路由层         │
              │   (DNS / 负载均衡)       │
              └────────┬────────────────┘
          ┌────────────┼────────────────┐
          ▼            ▼                ▼
   ┌──────────┐  ┌──────────┐   ┌──────────┐
   │ 北京DC   │  │ 上海DC   │   │ 美国DC   │
   │          │  │          │   │          │
   │ ┌──────┐ │  │ ┌──────┐ │   │ ┌──────┐ │
   │ │Redis │ │  │ │Redis │ │   │ │Redis │ │
   │ │集群   │ │  │ │集群   │ │   │ │集群   │ │
   │ └──────┘ │  │ └──────┘ │   │ └──────┘ │
   │          │  │          │   │          │
   │ 本DC读写  │  │ 本DC读写  │   │ 本DC读写  │
   └─────┬────┘  └────┬─────┘   └─────┬────┘
         │            │               │
         └────────────┼───────────────┘
                      │
              异步复制 (CRDTs / 双向同步)
              冲突解决：Last-Write-Wins / 自定义合并

方案对比：
┌───────────────┬──────────────────────────────────────────┐
│ 方案           │ 适用场景                                  │
├───────────────┼──────────────────────────────────────────┤
│ 主从复制       │ 读多写少，可容忍跨DC延迟                   │
│ Redis-shake   │ 阿里开源，支持增量同步                      │
│ CRDT-Redis    │ 读写都分散，需要最终一致性                  │
│ Proxy 层路由   │ 一致性要求高，通过 Proxy 路由到主DC写入     │
└───────────────┴──────────────────────────────────────────┘
```

### 10.3 大厂常见中间件

```
┌─────────────────────────────────────────────────────────────┐
│ 工具                 │ 公司      │ 用途                       │
├──────────────────────┼──────────┼────────────────────────────┤
│ Codis                │ 豆瓣     │ Redis 集群代理（Proxy模式）  │
│ Twemproxy (nutcracker)│ Twitter  │ 轻量级 Proxy 分片           │
│ Redis Cluster        │ Redis官方│ 去中心化集群                 │
│ Tair                  │ 阿里     │ 增强版 Redis（多数据结构）   │
│ Pika                  │ 360      │ 磁盘存储兼容 Redis 协议     │
│ Kvrocks               │ 美团开源 │ 磁盘存储，RocksDB后端       │
│ Redis-shake           │ 阿里     │ 数据同步/迁移工具           │
│ CacheCloud            │ 搜狐     │ Redis 运维管理平台          │
│ Predixy               │ 社区     │ 高性能 Proxy               │
│ KeyDB                 │ Snap     │ Redis 多线程 fork          │
│ Dragonfly             │ 社区     │ 替代 Redis 的多线程内存数据库│
└─────────────────────────────────────────────────────────────┘
```

---

## 十一、源码级监控指标

```bash
# 逐条命令分析（生产慎用，性能损耗极大）
redis-cli MONITOR | pv -l -i 5 -r > /dev/null
# 实时 QPS 观测

# 关键延迟诊断
redis-cli --latency                    # 持续测量延迟
redis-cli --latency-history -i 5       # 每5秒输出一次延迟统计
redis-cli --latency-dist               # 延迟分布图

# 内存诊断
redis-cli MEMORY DOCTOR                # 内存健康诊断
redis-cli MEMORY STATS                 # 详细内存统计
redis-cli MEMORY USAGE key [SAMPLES N] # 精确计算单个key内存

# 关键大厂监控项（Prometheus + Grafana）
```

```
指标分类与告警阈值：

━━ 延迟指标 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
latency_percentile_usec.p99 < 1000      # P99 < 1ms
latency_percentile_usec.p999 < 5000     # P999 < 5ms
latency_spike_duration_seconds = 0      # 无持续延迟尖峰

━━ 内存指标 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
used_memory / maxmemory < 0.8           # 内存使用率 < 80%
mem_fragmentation_ratio ∈ [1.0, 1.5]   # 碎片率正常
evicted_keys = 0                         # 无淘汰
used_memory_dataset_perc > 50%          # 数据占比（非元数据开销）

━━ 命令指标 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
instantaneous_ops_per_sec < 容量上限     # QPS
instantaneous_input_kbps < 带宽上限      # 输入带宽
instantaneous_output_kbps < 带宽上限     # 输出带宽
latest_fork_usec < 100000               # fork 耗时 < 100ms

━━ 复制指标 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
master_repl_offset - slave_offset < 1MB  # 复制延迟
repl_backlog_active = 1                  # 积压缓冲区活跃
connected_slaves >= min_replicas_to_write

━━ 集群指标 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cluster_state = ok                       # 集群状态
cluster_slots_ok = 16384                 # 所有 slot 正常
cluster_slots_pfail = 0
cluster_slots_fail = 0

━━ 持久化指标 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
rdb_last_bgsave_status = ok
aof_last_bgrewrite_status = ok
aof_last_write_status = ok
rdb_last_cow_size < maxmemory * 0.5     # COW 内存 < 50%

━━ 客户端指标 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
connected_clients < maxclients * 0.8
blocked_clients = 0（持续为0）
rejected_connections = 0
```

---

## 十二、Redis 7.0/7.2/7.4 新特性速览

```
Redis 7.0（2022年）：
├── Function（替代 EVAL/EVALSHA 的持久化函数）
├── Multi-Part AOF（多部件AOF，基线+增量）
├── ACL v2（更细粒度的权限控制）
├── listpack 全面替代 ziplist
├── Client-side caching tracking v2（广播模式 + 普通模式）
├── Sharded Pub/Sub（分片发布订阅）
└── EXPIRETIME / PEXPIRETIME 命令

Redis 7.2（2023年）：
├── WAITAOF 命令（等待 AOF fsync 确认）
├── 增强的 CLUSTER SHARDS 命令
├── CLIENT NO-EVICT（连接级别免淘汰）
├── Lua 脚本改进
└── 性能优化

Redis 7.4（2024年）：
├── Hash 字段级 TTL（HEXPIRE/HPEXPIRE）
├── 改进的 CLIENT TRACKING
└── 更多性能优化

Hash Field TTL 示例（7.4+）：
HSET user:1000 name "Tom" age "25"
HEXPIRE user:1000 3600 FIELDS 1 name    # name 字段 1小时后过期
HTTL user:1000 FIELDS 2 name age        # 查看字段TTL
```

---

## 总结：大厂面试高频 Top 10

```
1.  Redis 单线程为什么这么快？（IO多路复用+纯内存+避免锁）
2.  渐进式 Rehash 的过程和触发条件？（负载因子 + BGSAVE影响）
3.  RDB + AOF + 混合持久化的区别和选择？（数据安全 vs 性能）
4.  fork() COW 的原理和风险？（内存翻倍 + OOM killer）
5.  集群故障转移和选举过程？（PFAIL → FAIL → 选举 → 多数票）
6.  大Key/热Key 的检测和解决方案？（UNLINK + 本地缓存 + 拆分）
7.  分布式锁的实现和 Redisson Watch Dog？（Lua原子 + 续期）
8.  缓存穿透/击穿/雪崩的区别和解决方案？（布隆过滤器 + 互斥锁 + TTL随机）
9.  Redis 6.0 IO 多线程的实现原理？（IO线程并发读写，命令单线程执行）
10. PSYNC2 故障转移后增量同步的原理？（双 replid + second_replid_offset）
```

以上覆盖了大厂面试和生产环境中 Redis 底层的全部核心细节。每个知识点都对应了源码级实现和真实生产问题的解决方案。
