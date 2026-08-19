---
title: 阿里盘古（Pangu）分布式文件系统 — 底层细节深度解析
date: 2026-09-07 21:30:00
tags:
  - 盘古
  - 分布式存储
  - 阿里云
  - 文件系统
categories:
  - 分布式系统
---

> **说明**：以下内容基于阿里公开的技术博客、会议演讲（ArchSummit、QCon、FAST、ATC）、以及工程文章整理而成。部分实现细节属于合理推断，非官方源码级确认。

---

## 一、盘古的历史演进

```
时间轴:

2009  ┃ Pangu 0.1 — 阿里云成立，飞天（Apsara）操作系统启动
      ┃            盘古作为飞天的存储底座诞生
      ┃            架构参考 GFS，单 Master + ChunkServer
      ┃
2011  ┃ Pangu 1.0 — 服务阿里云 OSS/ECS/RDS 等核心产品
      ┃            三副本，64MB Chunk
      ┃            单 Master 成为瓶颈
      ┃
2015  ┃ Pangu 1.5 — Master 分片，引入 Raft 共识
      ┃            支持 EC 纠删码
      ┃            SSD 缓存层
      ┃
2018  ┃ Pangu 2.0 — 全面重构
      ┃            多 Master 分片 + Paxos/Raft
      ┃            小文件合并存储
      ┃            存储计算分离架构
      ┃
2021  ┃ Pangu 2.5 — 支持 RDMA 网络
      ┃            全用户态 I/O 栈
      ┃            百万级 IOPS 单节点
      ┃
2023+ ┃ Pangu 3.0 — 面向 AI 大模型训练的存储优化
      ┃            万亿参数模型 checkpoint 存储
      ┃            磁带/光存储冷归档层
      ┃            软硬件协同设计（定制 SSD 控制器）
```

---

## 二、总体架构

### 2.1 三平面架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Control Plane（管控平面）              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Cluster Master│  │ Monitor      │  │ Scheduler    │       │
│  │ (集群元数据)   │  │ (健康监控)    │  │ (负载调度)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                        Meta Plane（元数据平面）               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Pangu Master（分片元数据服务）               │    │
│  │  ┌────────┬────────┬────────┬────────┬────────┐     │    │
│  │  │Shard 0 │Shard 1 │Shard 2 │  ...   │Shard N │     │    │
│  │  │(Paxos) │(Paxos) │(Paxos) │        │(Paxos) │     │    │
│  │  └────────┴────────┴────────┴────────┴────────┘     │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                        Data Plane（数据平面）                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ChunkServer│ │ChunkServer│ │ChunkServer│ │ChunkServer│     │
│  │ Node 0   │ │ Node 1   │ │ Node 2   │ │ Node M   │       │
│  │┌────────┐│ │┌────────┐│ │┌────────┐│ │┌────────┐│       │
│  ││NVMe SSD││ ││NVMe SSD││ ││NVMe SSD││ ││HDD     ││       │
│  ││NVMe SSD││ ││NVMe SSD││ ││NVMe SSD││ ││HDD     ││       │
│  ││HDD     ││ ││HDD     ││ ││HDD     ││ ││HDD     ││       │
│  │└────────┘│ │└────────┘│ │└────────┘│ │└────────┘│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 进程模型

每台物理机上运行的盘古进程：

```
物理机 (ChunkServer Node)
├── pangu_chunkserver    // 数据服务进程（多实例，每块盘一个）
│   ├── IO Thread Pool   // I/O 线程池，绑定 CPU Core
│   ├── Network Thread    // 网络收发（RDMA / TCP）
│   ├── Checksum Thread   // 后台校验
│   └── Replication Thread // 副本同步
│
├── pangu_agent          // 本地代理进程
│   ├── 磁盘健康检测 (SMART)
│   ├── 硬件监控 (温度/功耗)
│   └── 与管控平面通信
│
└── pangu_cache          // SSD 缓存进程 (可选)
    ├── Read Cache (读缓存)
    └── Write Buffer (写缓冲)
```

---

## 三、Master 元数据系统

### 3.1 元数据分片（Sharding）

盘古 2.0 的核心改进之一：**Master 从单点变为分布式分片**。

```
分片策略：基于文件路径的 Range 分片

Namespace 分片示例:

  Shard 0: ["/a", "/b/foo")        → Master 节点 A
  Shard 1: ["/b/foo", "/d")        → Master 节点 B  
  Shard 2: ["/d", "/m")            → Master 节点 C
  Shard 3: ["/m", "/z")            → Master 节点 D

每个 Shard 是一个 Raft Group (3 节点或 5 节点):

  Shard 0:
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │ Node A      │  │ Node E      │  │ Node F      │
  │ (Leader)    │←→│ (Follower)  │←→│ (Follower)  │
  │ Raft Log    │  │ Raft Log    │  │ Raft Log    │
  │ State Machine│  │ State Machine│  │ State Machine│
  └─────────────┘  └─────────────┘  └─────────────┘
       ↑
       │ 写入元数据
     Client
```

### 3.2 元数据存储引擎

```cpp
// 每个 Master Shard 内部的存储结构
class PanguMasterShard {
    // 核心数据结构：内存 + 持久化
    struct NamespaceEntry {
        std::string     path;          // 文件路径
        FileType        type;          // 普通文件 / 目录 / 符号链接
        uint64_t        file_size;     // 文件大小
        uint64_t        mtime;         // 修改时间
        uint32_t        permission;    // 权限
        ChunkList       chunks;        // 该文件的 Chunk 列表
        // ChunkList: [(chunk_id_0, version_0), (chunk_id_1, version_1), ...]
    };

    struct ChunkEntry {
        uint64_t        chunk_id;      // 全局唯一 Chunk ID
        uint32_t        version;       // 版本号（每次 Primary 变更递增）
        uint64_t        chunk_size;    // 当前 Chunk 大小
        ChunkState      state;         // FINALIZED / APPENDABLE / DELETED
        ReplicaList     replicas;      // [(server_id, disk_id), ...]
        uint64_t        lease_holder;  // 持有 Lease 的 ChunkServer ID
        uint64_t        lease_expire;  // Lease 过期时间
    };

    // 持久化层：WAL + 快照
    RaftLog            raft_log_;      // Raft 日志（写入 SSD）
    LSMTree*           meta_store_;    // 元数据持久化（RocksDB 风格）
    MemTable*          mem_cache_;     // 内存缓存（热数据）
};
```

### 3.3 元数据操作流程

```
Client 创建文件: CreateFile("/data/oss/bucket1/photo.jpg")

1. Client → Routing Layer: 
   根据路径哈希确定 Shard → Shard 2 (负责 /d ~ /m)

2. Routing Layer → Shard 2 Leader:
   CreateFile RPC 请求

3. Shard 2 Leader:
   a. 写 Raft Log: {op: CREATE, path: "/data/oss/bucket1/photo.jpg", ...}
   b. 等待多数 Follower 确认
   c. 应用到 State Machine → 写入 LSMTree
   d. 分配 Chunk ID（全局唯一 ID 分配器）
   e. 选择 ChunkServer 副本位置

4. 返回给 Client:
   {file_handle, chunk_id, chunk_servers, lease_holder}
```

### 3.4 Chunk ID 分配器

```
全局唯一 Chunk ID 生成策略：

  ┌─────────────────────────────────────────────┐
  │         64-bit Chunk ID                      │
  ├──────────────────┬──────────────────────────┤
  │  Shard ID (16b)  │  Local Sequence (48b)    │
  │  标识哪个 Master  │  该 Shard 内自增序列号    │
  │  Shard 负责此 Chunk│                         │
  └──────────────────┴──────────────────────────┘

  优势：
  - Chunk ID 本身编码了归属 Shard 信息
  - 恢复时可以直接路由到正确的 Shard
  - 48 位序列号足够用了（2^48 ≈ 281 万亿）
```

---

## 四、数据路径（Data Path）

### 4.1 写路径 — 副本模式

```
完整写路径 (Append Write):

  Client                Pangu Master              Primary CS        Secondary CS
    │                        │                        │                  │
    │── 1. Lookup ──────────→│                        │                  │
    │←─ (chunk_id, replicas, │                        │                  │
    │    lease_holder) ──────│                        │                  │
    │                        │                        │                  │
    │── 2. Push Data ────────────────────────────────→│                  │
    │    (pipeline: CS1→CS2→CS3, RDMA WRITE)          │── Forward ──────→│
    │                        │                        │                  │
    │── 3. Write Request ───────────────────────────→│                  │
    │    (chunk_id, offset, length, op_id)            │                  │
    │                        │                        │                  │
    │                        │   4. Primary 确定写入顺序                    │
    │                        │      将操作发送给所有 Secondary              │
    │                        │                        │── 5. Apply ─────→│
    │                        │                        │   (写 WAL + Data) │
    │                        │                        │←── ACK ─────────│
    │                        │                        │                  │
    │                        │   6. Primary 等待多数 ACK 后提交             │
    │←── 7. Write ACK ──────────────────────────────│                  │
    │                        │                        │                  │
```

### 4.2 数据写入细节 — ChunkServer 内部

```
ChunkServer 收到写请求后的处理:

┌─────────────────────────────────────────────────────┐
│                ChunkServer 内部                       │
│                                                     │
│  ┌──────────────┐     ┌──────────────┐              │
│  │ Network Layer │────→│ Request Queue│              │
│  │ (RDMA Recv)   │     │ (Lock-free)  │              │
│  └──────────────┘     └──────┬───────┘              │
│                              │                      │
│                       ┌──────▼───────┐              │
│                       │ I/O Scheduler │              │
│                       │ (合并/排序)    │              │
│                       └──────┬───────┘              │
│                              │                      │
│                    ┌─────────▼─────────┐            │
│                    │   Write Pipeline   │            │
│                    └─────────┬─────────┘            │
│                              │                      │
│              ┌───────────────┼───────────────┐      │
│              ▼               ▼               ▼      │
│     ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│     │  WAL Write  │  │ Data Write │  │ Csum Write │ │
│     │ (写预日志)   │  │ (写数据)    │  │ (写校验)   │ │
│     │ NVMe SSD    │  │ HDD/SSD    │  │ 附在数据后  │ │
│     └────────────┘  └────────────┘  └────────────┘ │
│              │               │               │      │
│              └───────┬───────┘               │      │
│                      ▼                       │      │
│              ┌────────────┐                  │      │
│              │   fsync()   │  ← 确保持久化     │      │
│              └────────────┘                  │      │
│                      │                       │      │
│                      ▼                       ▼      │
│              ┌──────────────────────────────────┐   │
│              │         ACK → Primary/Client      │   │
│              └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 4.3 WAL（Write-Ahead Log）设计

```
盘古的 WAL 不是简单的顺序日志文件，而是精心设计的:

WAL Segment 结构:
┌─────────────────────────────────────────────┐
│ Segment Header (magic, version, crc)        │
├─────────────────────────────────────────────┤
│ Log Entry 0                                 │
│   ├── LSN (Log Sequence Number, 64-bit 单调递增) │
│   ├── Chunk ID                              │
│   ├── Offset                                │
│   ├── Length                                │
│   ├── Operation Type (WRITE/APPEND/TRUNCATE)│
│   ├── Checksum                              │
│   └── Data (可选，小写入内嵌数据)              │
├─────────────────────────────────────────────┤
│ Log Entry 1                                 │
│ ...                                         │
├─────────────────────────────────────────────┤
│ Group Commit Marker (批量提交标记)            │
└─────────────────────────────────────────────┘

Group Commit 策略:
  不是每条写入都 fsync，而是累积 N 条或超时 T 毫秒后一次 fsync
  典型配置: N=64 或 T=1ms
  → 显著降低 fsync 次数，提高吞吐

WAL 写入 SSD (NVMe):
  使用 DIRECT I/O + io_uring 异步提交
  单盘 WAL 吞吐: ~2 GB/s
```

### 4.4 RDMA 数据传输

盘古 2.5+ 大规模使用 **RDMA (Remote Direct Memory Access)**：

```
传统 TCP 传输路径:
  App Buffer → Kernel Buffer → NIC → 网络 → NIC → Kernel Buffer → App Buffer
  延迟: ~50μs (每次经过内核都有开销)

RDMA 传输路径:
  App Buffer → NIC (DMA 直接读取) → 网络 → NIC (DMA 直接写入) → App Buffer
  延迟: ~5μs
  
盘古中的 RDMA 使用方式:

  1. 写数据推送 (Pipeline):
     Client ──RDMA WRITE──→ Primary CS 内存
     Primary CS ──RDMA WRITE──→ Secondary CS 内存
     (零拷贝，直接写入远端内存，无需远端 CPU 参与)

  2. 小消息控制:
     使用 RDMA SEND/RECV (类似消息传递)
     用于写请求确认、心跳等

  3. 内存注册 (Memory Registration):
     ChunkServer 启动时预注册一大块内存作为 RDMA Buffer
     ┌────────────────────────────────────┐
     │  Pre-registered RDMA Buffer Pool   │
     │  ┌──────┐┌──────┐┌──────┐┌──────┐ │
     │  │ Buf0 ││ Buf1 ││ Buf2 ││ ...  │ │
     │  │ 4MB  ││ 4MB  ││ 4MB  ││      │ │
     │  └──────┘└──────┘└──────┘└──────┘ │
     │  每个 Buffer 对应一个 Memory Region │
     │  (lkey/rkey 用于远端 DMA 授权)      │
     └────────────────────────────────────┘
```

---

## 五、Chunk 内部组织

### 5.1 Chunk 物理布局

```
盘古的 Chunk 在磁盘上的真实布局 (简化):

┌─────────────────────────────────────────────────────────────┐
│                     Chunk File (例如 256MB)                   │
├─────────────────────────────────────────────────────────────┤
│ Chunk Header (4KB)                                          │
│   ├── Magic Number                                           │
│   ├── Chunk ID (8 bytes)                                     │
│   ├── Version (4 bytes)                                      │
│   ├── Chunk Size (8 bytes)                                   │
│   ├── State (FINALIZED / APPENDABLE)                         │
│   ├── Replica Count                                          │
│   └── Header Checksum                                        │
├─────────────────────────────────────────────────────────────┤
│ Data Region                                                 │
│   ┌─────────────────────────┐                               │
│   │ Block 0 (64KB)          │  ← 每个 Block 带独立 Checksum  │
│   │  Data: 65536 bytes      │                               │
│   │  CRC32C: 4 bytes        │                               │
│   ├─────────────────────────┤                               │
│   │ Block 1 (64KB)          │                               │
│   │  ...                    │                               │
│   ├─────────────────────────┤                               │
│   │ ...                     │                               │
│   ├─────────────────────────┤                               │
│   │ Block N                 │                               │
│   └─────────────────────────┘                               │
├─────────────────────────────────────────────────────────────┤
│ Checksum Region (尾部)                                       │
│   ┌─────────────────────────────────────────┐               │
│   │ Block 0 CRC32C                           │               │
│   │ Block 1 CRC32C                           │               │
│   │ ...                                      │               │
│   │ Block N CRC32C                           │               │
│   │ Checksum Region CRC32C (元校验)           │               │
│   └─────────────────────────────────────────┘               │
├─────────────────────────────────────────────────────────────┤
│ Index Region (可选，用于 Append 模式)                         │
│   记录每条 Append Record 的 offset 和 length                  │
│   用于故障恢复时重建索引                                       │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Chunk 大小策略

```
盘古根据使用场景采用不同的 Chunk Size:

  场景                  Chunk Size    原因
  ──────────────────────────────────────────────────
  OSS 大对象存储         64 MB        大文件顺序写，减少元数据
  ECS 云盘 (随机读写)    64 KB ~ 1 MB  小粒度，减少写放大
  数据库 WAL             4 KB ~ 64 KB  对齐数据库页
  小文件合并存储          256 MB       Container 内聚合
  冷数据归档             256 MB       大块减少 EC 编码碎片
  AI 训练 Checkpoint     64 MB        大文件突发写入

  关键设计: Chunk Size 在文件创建时确定，后续不可变
```

---

## 六、一致性协议

### 6.1 Chunk 级别的 Raft/Paxos

```
盘古 2.0 的核心变化: 每个 Chunk 是一个独立的一致性组

  Chunk 0xBEEF:
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │ Server A    │  │ Server B    │  │ Server C    │
  │ (Leader)    │  │ (Follower)  │  │ (Follower)  │
  │             │  │             │  │             │
  │ Raft Log:   │  │ Raft Log:   │  │ Raft Log:   │
  │  #1 WRITE   │  │  #1 WRITE   │  │  #1 WRITE   │
  │  #2 WRITE   │  │  #2 WRITE   │  │  #2 WRITE   │
  │  #3 APPEND  │  │  #3 APPEND  │  │             │ ← 还没追上
  │             │  │             │  │             │
  │ Data File:  │  │ Data File:  │  │ Data File:  │
  │  [64MB]     │  │  [64MB]     │  │  [63MB]     │ ← 还在同步
  └─────────────┘  └─────────────┘  └─────────────┘

  一个集群可能有上百万个 Chunk → 上百万个 Raft Group
  → Multi-Raft 架构（类似 TiKV 的 Multi-Raft）

  Raft Log 存储:
    Raft Log 和 Data 分开存储
    Raft Log → NVMe SSD（低延迟）
    Data     → HDD 或 SSD（大容量/高吞吐）
```

### 6.2 Leader 选举优化

```
标准 Raft 选举的超时是 150~300ms（随机化）

盘古的优化:

  1. Pre-vote 机制:
     在正式发起选举前，先发 PreVote 请求
     确认自己能获得多数票才真正递增 Term
     → 避免网络抖动导致的无效选举和 Term 膨胀

  2. 优先级选举 (Priority Election):
     每个 Follower 有一个优先级分数
     优先级 = f(数据最新程度, 机器负载, 机架位置)
     数据最新的 Follower 优先当选
     → 减少新 Leader 的日志追赶时间

  3. 闪电选举 (Fast Election):
     Leader 在主动下线前，推荐一个 Follower 作为继任者
     ┌──────────┐                    ┌──────────┐
     │ Leader   │── TransferLeader → │ Follower │
     │ (下线前)  │                    │ (立即成为 │
     │          │                    │  Leader)  │
     └──────────┘                    └──────────┘
     → 选举延迟从 ~200ms 降到 ~1ms
```

### 6.3 Lease 机制（仍保留用于读优化）

```
即使有了 Raft，盘古仍保留 Lease 用于优化读:

  Leader 持有 Lease:
    Leader 定期向 Follower 发心跳
    Follower 回复心跳 = 隐式续约 Lease
    Leader 在 Lease 有效期内可以直接响应读请求 (Read Lease)

  Follower Read:
    方式一: Lease Read — Leader 可直接读（无 RPC）
    方式二: Follower Read — 需要向 Leader 确认自己仍是 Leader
           (ReadIndex 方案，一次额外 RPC)
    方式三: Stale Read — 直接读 Follower 数据（可能过时）
           用于对一致性要求不高的场景（如日志查看）

  盘古根据业务 SLA 选择读策略:
    OSS 读: Stale Read (允许短暂不一致)
    数据库底座: Lease Read / ReadIndex (强一致)
```

---

## 七、小文件合并存储

### 7.1 Super Block 设计

这是盘古应对 **OSS 海量小图片/缩略图** 场景的核心优化：

```
问题:
  OSS 上 70%+ 的对象 < 1MB
  如果每个小对象一个 Chunk → 元数据爆炸 + 磁盘随机 I/O

解决方案: Super Block (超级块) 合并存储

Super Block (256 MB, 存在于 ChunkServer 的一个大文件中):
┌──────────────────────────────────────────────────────────────┐
│ Super Block Header                                           │
│   Magic: "PANGU_SB"                                          │
│   Version: 3                                                 │
│   Object Count: 524288                                       │
│   Free Offset: 250MB                                         │
│   Checksum: 0xABCD1234                                       │
├──────────────────────────────────────────────────────────────┤
│ Object Index Table (在文件尾部，从后往前生长)                    │
│   ┌──────────────────────────────────────────────────────┐   │
│   │ Entry 0: obj_id=0x0001, offset=0, len=512, csum=...  │   │
│   │ Entry 1: obj_id=0x0002, offset=512, len=1024, csum=..│   │
│   │ Entry 2: obj_id=0x0003, offset=1536, len=256, csum=. │   │
│   │ ... (每条 Entry 20 bytes)                             │   │
│   └──────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────────┤
│ Data Region (从前往后写入):                                    │
│   [obj_0x0001 data (512B)]                                   │
│   [obj_0x0002 data (1KB)]                                    │
│   [obj_0x0003 data (256B)]                                   │
│   [padding to 4KB alignment]                                 │
│   ...                                                        │
│   [free space]                                               │
│   ...                                                        │
├──────────────────────────────────────────────────────────────┤
│ ← Index Table 从这里向左生长                                   │
│ ← Data 从这里向右生长                                          │
│   两者相遇时 Super Block 满 → 新建一个 Super Block              │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 小文件的元数据路径

```
传统方式:
  文件路径 → Master 查元数据 → 返回 Chunk Location → 读 Chunk

小文件优化后:
  文件路径 → Master 查元数据 
         → 返回 (Super Block ID, offset, length)
         → 直接读 Super Block 的 [offset, offset+length)

  关键: Master 只存储 Super Block 粒度的映射
  一个 Super Block 覆盖 ~50 万个小文件
  → 元数据量减少 50 万倍
```

### 7.3 小文件的合并写入

```
写入流程 (批量合并):

  1. Client 发送 N 个小文件写请求
  2. ChunkServer 收集请求，在内存中组装:
     ┌────────────────────────────┐
     │ Memory Write Buffer        │
     │ [file_0 | file_1 | ... | file_N] │
     └────────────────────────────┘
  3. 累积到阈值 (如 4MB) 或超时 (如 10ms) 后:
     a. 追加写入 Super Block Data Region
     b. 更新 Object Index Table
     c. 单次 fsync
  4. 返回成功

  效果:
    原本 N 次 fsync → 1 次 fsync
    随机小写 → 顺序大写
    IOPS 从 ~200 (HDD) 提升到 ~50,000 (合并写)
```

---

## 八、Erasure Coding（纠删码）

### 8.1 盘古的 EC 实现

```
盘古支持的 EC 编码方案:

  模式          数据块  校验块  总块数  存储效率  容灾能力
  ─────────────────────────────────────────────────────
  3 副本         -       -      3      33%      容 2 故障
  RS(6,3)       6       3      9      67%      容 3 故障
  RS(8,4)       8       4     12      67%      容 4 故障
  RS(10,4)     10       4     14      71%      容 4 故障
  LRC(12,2,2)  12       4     16      75%      容 2 局部 + 2 全局

  LRC = Locally Repairable Code (局部可修复码)
  优势: 单块盘故障只需从 2 个块恢复 (而不是 RS 的 10 个块)
```

### 8.2 EC Stripe 布局

```
一个文件的 EC Stripe (以 RS(6,3) 为例):

原始数据 (64 MB):
  Chunk D0, D1, D2, D3, D4, D5 (各 ~10.67 MB)

编码计算:
  P0 = f(D0, D1, D2, D3, D4, D5)  // 校验块 0
  P1 = g(D0, D1, D2, D3, D4, D5)  // 校验块 1  
  P2 = h(D0, D1, D2, D3, D4, D5)  // 校验块 2

物理放置 (跨 9 台不同机器):

  Machine 0: D0
  Machine 1: D1
  Machine 2: D2
  Machine 3: D3
  Machine 4: D4
  Machine 5: D5
  Machine 6: P0
  Machine 7: P1
  Machine 8: P2

  约束: 任意 9 台机器不在同一机架

  Stripe 元数据存储在 Master:
    stripe_id → [(machine_0, chunk_D0), ..., (machine_8, chunk_P2)]
```

### 8.3 EC 的在线修复

```
当 Machine 2 (存储 D2) 故障时:

  修复方案一: 远程修复 (Remote Repair)
    需要从 6 台机器读取 D0,D1,D3,D4,D5 (或任意 6 个块)
    在修复节点计算 D2' = f_inv(D0,D1,D3,D4,D5,P0) 或类似
    传输量: 6 × 10.67MB = 64MB (读放放大 6 倍)

  修复方案二: 局部修复 (LRC Local Repair)
    如果使用 LRC(12,2,2)，局部校验块 PL 覆盖 D0~D5
    只需从 2 台机器读取数据即可恢复
    传输量: 2 × 10.67MB = 21.3MB (读放放大 2 倍)

  盘古的修复调度:
    ┌─────────────────────────────────────────────┐
    │  Repair Scheduler                            │
    │                                              │
    │  优先级队列:                                   │
    │    P0: 只有 1 个副本的 Chunk (极度危险)         │
    │    P1: EC Stripe 中已丢失 1 块 (还可容灾)       │
    │    P2: EC Stripe 中已丢失 2 块 (紧急)           │
    │                                              │
    │  带宽限制:                                     │
    │    修复带宽不超过集群总带宽的 30%                 │
    │    避免修复风暴影响正常业务                       │
    │                                              │
    │  修复源选择:                                    │
    │    优先从同机架的副本读 (减少跨机架流量)           │
    └─────────────────────────────────────────────┘
```

---

## 九、分层存储管理

### 9.1 存储分层

```
盘古的四层存储模型:

┌────────────────────────────────────────────────────────┐
│ Layer 0: Ultra (NVMe SSD, 3D NAND)                    │
│   延迟: 0.05~0.1ms  IOPS: 50万+  带宽: 6 GB/s         │
│   用途: WAL, 元数据, 热数据缓存                          │
│   副本策略: 3 副本                                      │
├────────────────────────────────────────────────────────┤
│ Layer 1: Performance (SATA SSD / High-perf HDD)        │
│   延迟: 0.5~2ms  IOPS: 5千~5万  带宽: 500 MB/s         │
│   用途: 频繁读写的业务数据                               │
│   副本策略: 3 副本                                      │
├────────────────────────────────────────────────────────┤
│ Layer 2: Standard (普通 HDD)                            │
│   延迟: 5~10ms  IOPS: 100~200  带宽: 200 MB/s          │
│   用途: 普通业务数据                                     │
│   副本策略: EC(6,3) 或 2 副本 + EC                     │
├────────────────────────────────────────────────────────┤
│ Layer 3: Archive (高密度 HDD / 磁带库)                   │
│   延迟: 秒~分钟级  容量: EB 级                           │
│   用途: 合规归档, 冷数据, 数据湖                          │
│   副本策略: EC(10,4), 单副本 + EC                      │
└────────────────────────────────────────────────────────┘

数据生命周期:
  写入 → Layer 0/1 (根据业务 QoS)
  7天无访问 → 降级到 Layer 2 (自动迁移 + 编码转换)
  30天无访问 → 降级到 Layer 3 (EC 编码 + 压缩)
  用户请求 → 升级到 Layer 1 (预取)
```

### 9.2 ILM (Information Lifecycle Management) 引擎

```python
# 盘古 ILM 的简化逻辑
class PanguILM:
    def evaluate(self, chunk: Chunk) -> Action:
        access_pattern = self.analyze_access(chunk)
        age = time.now() - chunk.last_access_time
        current_tier = chunk.tier
        
        # 规则引擎
        if access_pattern == "HOT":
            if current_tier != TIER_ULTRA:
                return Action.PROMOTE(target_tier=TIER_ULTRA)
                
        elif access_pattern == "WARM":
            if current_tier == TIER_ULTRA and age > 1_DAY:
                return Action.DEMOTE(target_tier=TIER_PERF)
                
        elif access_pattern == "COLD":
            if age > 7_DAYS and current_tier < TIER_STANDARD:
                # 同时转换: 3副本 → EC(6,3)
                return Action.DEMOTE(
                    target_tier=TIER_STANDARD,
                    encoding_change=(REPLICA_3, EC_6_3)
                )
            if age > 30_DAYS and current_tier < TIER_ARCHIVE:
                return Action.DEMOTE(
                    target_tier=TIER_ARCHIVE,
                    encoding_change=(EC_6_3, EC_10_4)
                )
        
        return Action.NOOP
    
    def analyze_access(self, chunk) -> str:
        # 基于滑动窗口统计访问频率
        reads_1h = chunk.read_count(window=1_HOUR)
        reads_24h = chunk.read_count(window=24_HOURS)
        
        if reads_1h > 100:
            return "HOT"
        elif reads_24h > 10:
            return "WARM"
        else:
            return "COLD"
```

---

## 十、故障模型与恢复

### 10.1 盘古定义的故障类型

```
故障分级:

  Level 1: 磁盘故障 (单盘)
    恢复时间: 分钟级
    影响范围: 该盘上的 Chunk 副本
    年化概率: 1~3% (AFR)

  Level 2: 机器故障 (单机)
    恢复时间: 分钟~小时级
    影响范围: 该机器上所有磁盘的所有 Chunk
    年化概率: 5~10%

  Level 3: 机架故障 (交换机/电源)
    恢复时间: 小时级
    影响范围: 整个机架 (30~60 台机器)
    年化概率: 1~2%

  Level 4: 机房级故障 (数据中心局部)
    恢复时间: 天级
    影响范围: 数千台机器
    年化概率: < 0.1%
```

### 10.2 磁盘故障检测与恢复

```
盘古的磁盘健康管理系统:

  ┌──────────────────────────────────────────────┐
  │         Disk Health Monitor (pangu_agent)     │
  │                                               │
  │  ┌─────────────────────┐                      │
  │  │ SMART 数据采集 (每5分)│                      │
  │  │  - Reallocated_Sect  │                      │
  │  │  - Pending_Sector    │                      │
  │  │  - UDMA_CRC_Error    │                      │
  │  │  - Temperature       │                      │
  │  └─────────┬───────────┘                      │
  │            ▼                                   │
  │  ┌─────────────────────┐                      │
  │  │ 故障预测模型 (ML)     │                      │
  │  │ 输入: SMART 特征     │                      │
  │  │ 输出: 故障概率 (0~1)  │                      │
  │  └─────────┬───────────┘                      │
  │            ▼                                   │
  │  ┌─────────────────────────────────┐          │
  │  │ 状态机:                          │          │
  │  │                                  │          │
  │  │  HEALTHY ──→ SUSPECT ──→ FAILING │          │
  │  │    │           │          │      │          │
  │  │    │     prob>0.3    prob>0.8    │          │
  │  │    │           │          ▼      │          │
  │  │    │           │       FAILED    │          │
  │  │    │           │          │      │          │
  │  │    │           ▼          ▼      │          │
  │  │    │     主动迁移数据  强制摘除     │          │
  │  └────┴─────────────────────────────┘          │
  └──────────────────────────────────────────────┘

  SUSPECT 状态处理:
    1. 不再向该盘分配新 Chunk
    2. 启动后台迁移 (drain): 将该盘数据复制到其他盘
    3. 迁移完成后标记为 FAILED，下线

  相比等磁盘彻底坏了再处理:
    SUSPECT 阶段迁移 = 有完整副本作为源，安全且快速
    等到 FAILED = 可能已有数据损坏，需要从远端副本修复
```

### 10.3 数据校验巡检 (Scrubbing)

```
后台巡检进程 (低优先级 I/O):

  ┌─────────────────────────────────────────────┐
  │  Scrubber Thread (每台 ChunkServer 1~2 个)    │
  │                                              │
  │  工作周期: 每 7 天扫完所有数据一次              │
  │                                              │
  │  对每个 Chunk:                                │
  │    1. 读取 Data Block                        │
  │    2. 计算 CRC32C                            │
  │    3. 对比 Checksum Region 中存储的校验值      │
  │    4. 如果不一致:                              │
  │       a. 标记该 Block 为 CORRUPT              │
  │       b. 从其他副本读取正确数据                │
  │       c. 修复本地副本                         │
  │       d. 上报 Master (统计静默损坏率)          │
  │                                              │
  │  I/O 限制:                                    │
  │    巡检带宽 ≤ 磁盘总带宽的 10%                  │
  │    业务 I/O 优先级高于巡检 I/O                  │
  └─────────────────────────────────────────────┘

  发现的典型问题:
    - 静默数据损坏 (Bit Rot): 磁盘物理劣化导致
    - 写入不完整: 断电导致部分写
    - 软件 Bug: Checksum 计算错误
```

---

## 十一、性能优化细节

### 11.1 I/O 调度器

```
盘古 ChunkServer 的 I/O 调度栈:

  应用层 I/O 请求
       │
       ▼
  ┌──────────────────┐
  │ Request Coalescer │  ← 合并相邻/重叠的 I/O
  │ (合并器)           │     例: [0~4K] + [4K~8K] → [0~8K]
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │ Priority Queue    │  ← 按优先级分队列
  │                   │     HIGH: 用户读请求
  │                   │     MED:  副本同步
  │                   │     LOW:  后台巡检/修复
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │ I/O Sorter        │  ← 按 LBA (磁盘地址) 排序
  │ (电梯算法)         │     减少磁头寻道距离
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │ Batch Submitter   │  ← 批量提交
  │ (io_uring)        │     每批 32~128 个 I/O
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │ 磁盘/NVMe 驱动    │
  └──────────────────┘

关键指标:
  HDD: 随机 IOPS ~200 → 排序+合并后有效 IOPS ~2000
  NVMe: 随机 IOPS ~50万 → 批量提交后 ~80万
```

### 11.2 内存管理

```
盘古 ChunkServer 的内存布局:

  总内存: 128 GB (典型配置)

  ┌─────────────────────────────────────────────┐
  │ 内存分配                                     │
  ├─────────────────────────────────────────────┤
  │ Raft Log Buffer:       4 GB   (Raft 日志缓存)  │
  │ Write Buffer:         16 GB   (写入缓冲区)      │
  │ Read Cache:           64 GB   (读缓存, LRU)     │
  │ RDMA Buffer:           8 GB   (RDMA 注册内存)    │
  │ Checksum Buffer:       4 GB   (校验计算缓冲)     │
  │ Index Cache:           8 GB   (小文件索引缓存)    │
  │ 元数据/其他:           24 GB                    │
  └─────────────────────────────────────────────┘

  Read Cache (读缓存) 策略:
    使用 LIRS (Low Inter-reference Recurrence Set) 算法
    比 LRU 更好地处理扫描模式（避免 Cache 污染）
    
    热点数据统计:
      每个 Chunk 维护访问计数器
      Top-1% 热点 Chunk 常驻缓存 (Pin)
```

### 11.3 网络优化

```
盘古的网络栈优化:

  1. 用户态协议栈 (DPDK/自研):
     绕过 Linux 内核网络栈
     直接从网卡 DMA 到用户空间
     减少 2 次内存拷贝 + 多次上下文切换

  2. 消息序列化:
     不用 JSON/Protobuf (太慢)
     使用 Flat Buffer 或自研零拷贝序列化:
     ┌──────────────────────────────┐
     │ Pangu Wire Format:            │
     │ Header (fixed 32 bytes)       │
     │   - msg_type (2B)             │
     │   - payload_len (4B)          │
     │   - request_id (8B)           │
     │   - checksum (4B)             │
     │   - flags (2B)                │
     │   - reserved (12B)            │
     │ Payload (variable)            │
     │   - 直接引用应用层 buffer      │
     │   - 零拷贝序列化               │
     └──────────────────────────────┘

  3. 连接管理:
     每对 ChunkServer 之间维持 N 个长连接 (Connection Pool)
     按消息大小路由:
       小消息 (<4KB): 走 TCP 连接 (避免 RDMA 控制面开销)
       大消息 (>4KB): 走 RDMA 连接
```

---

## 十二、面向 AI 场景的优化（Pangu 3.0）

### 12.1 大模型训练的存储挑战

```
典型 AI 训练场景:

  任务: 训练 1000 亿参数的大模型
  Checkpoint: 单次保存 ~400 GB (模型参数 + 优化器状态)
  保存频率: 每 30 分钟一次
  并发: 2048 个 GPU 同时写
  要求: Checkpoint 必须在 5 分钟内完成 (否则拖慢训练)

  挑战:
    400 GB / 5 min = ~1.3 GB/s 持续写入
    2048 路并发写入 → 单文件随机写 + 元数据风暴
```

### 12.2 盘古的 AI 优化

```
优化一: 专线 Checkpoint 通道
  ┌─────────────┐     ┌───────────────┐
  │ GPU 节点     │────→│ Checkpoint    │
  │ (训练集群)    │ RDMA│ 专用 ChunkServer│
  │             │     │ (NVMe Only)   │
  └─────────────┘     └───────────────┘
  专用的高速存储池，不与其他业务竞争

优化二: 分布式并行 Checkpoint
  不是 2048 个 GPU 写同一个文件
  而是每个 GPU Worker 写自己的分片:
    checkpoint_shard_0000.bin  →  CS-A
    checkpoint_shard_0001.bin  →  CS-B
    ...
    checkpoint_shard_2047.bin  →  CS-X
  充分利用所有 ChunkServer 的带宽

优化三: Incremental Checkpoint
  只保存自上次以来变化的参数块
  使用 Content-Defined Chunking 识别变更区域
  → Checkpoint 体积减少 60~80%

优化四: 异步持久化
  GPU 写入本地 NVMe → 立即返回 (checkpoint 完成)
  后台异步复制到分布式存储 (保证持久性)
  → 感知延迟从分钟级降到秒级
```

---

## 十三、可观测性体系

### 13.1 追踪系统

```
盘古内建分布式追踪:

  每个 I/O 请求生成一个 Trace:

  Trace ID: 0xABCD1234
  ┌───────────────────────────────────────────────────────┐
  │ Span 1: Client → Master (Lookup)                       │
  │   时间: 0μs ~ 200μs                                    │
  │   状态: OK                                              │
  ├───────────────────────────────────────────────────────┤
  │ Span 2: Client → Primary CS (Push Data)                │
  │   时间: 200μs ~ 1200μs                                  │
  │   子 Span:                                              │
  │     Span 2.1: CS-Primary → CS-Secondary1 (Forward)     │
  │       时间: 400μs ~ 800μs                               │
  │     Span 2.2: CS-Primary → CS-Secondary2 (Forward)     │
  │       时间: 400μs ~ 900μs                               │
  │   状态: OK                                              │
  ├───────────────────────────────────────────────────────┤
  │ Span 3: Client → Primary CS (Write Request)            │
  │   时间: 1200μs ~ 5000μs                                 │
  │   子 Span:                                              │
  │     Span 3.1: WAL Write (本地 NVMe)                     │
  │       时间: 1200μs ~ 1500μs                             │
  │     Span 3.2: Data Write (本地 HDD)                     │
  │       时间: 1500μs ~ 3000μs                             │
  │     Span 3.3: Replicate to Secondaries                  │
  │       时间: 1500μs ~ 4500μs                             │
  │     Span 3.4: fsync                                     │
  │       时间: 3000μs ~ 5000μs                             │
  │   状态: OK                                              │
  └───────────────────────────────────────────────────────┘
  
  总延迟: 5ms
  瓶颈分析: fsync 耗时 2ms (5000-3000), 可优化
```

### 13.2 核心监控指标

```
┌─────────────────────────────────────────────────────┐
│                 盘古监控大盘                           │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [延迟分布]                                          │
│  p50: 0.8ms  p90: 2.1ms  p99: 8.5ms  p999: 35ms   │
│  ██████████████████░░░░░░░░░░░░░░░░░░░░░░░░        │
│                                                     │
│  [吞吐]                                              │
│  写: 45 GB/s    读: 120 GB/s                         │
│  ████████████████████████████████████████            │
│                                                     │
│  [可靠性]                                            │
│  副本不足 Chunk: 47 (过去1小时修复了 12,034 个)        │
│  静默损坏: 0 (过去24小时)                              │
│  磁盘 SUSPECT: 3                                     │
│                                                     │
│  [容量]                                              │
│  总容量: 850 PB    已用: 612 PB (72%)                │
│  EC 有效率: 71% (vs 理论值 75%)                       │
│                                                     │
│  [Master 状态]                                       │
│  Shard 数: 256    Leader 数: 256                     │
│  Raft 延迟: p99 < 5ms                               │
│  Lease 命中率: 99.2%                                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 十四、盘古 vs 其他系统对比

| 维度 | 盘古 2.5+ | GFS/Colossus | Ceph RADOS | TiKV |
|------|-----------|-------------|------------|------|
| **定位** | 通用底座存储 | 大文件/数据分析 | 通用块/对象存储 | 分布式 KV |
| **元数据** | 分片 Raft | 分片 | CRUSH 无中心 | Raft |
| **数据一致性** | Multi-Raft | Lease+Primary | Raft | Raft |
| **EC 支持** | RS + LRC | RS | RS | 无(上层) |
| **小文件** | Super Block | Blob Store | 不擅长 | N/A |
| **网络** | RDMA+TCP | TCP | TCP | TCP |
| **I/O 栈** | 用户态 io_uring | 内核态 | 内核态 | 内核态 |
| **规模** | EB 级 | EB 级 | PB~EB 级 | PB 级 |
| **存储层次** | 4 层 | 3 层 | 2 层 | 1 层 |

---

## 总结

盘古的核心设计哲学可以概括为：

1. **分而治之**：Master 分片、Chunk 级 Raft Group、数据分层——每个维度都拆分以获得水平扩展能力。

2. **软硬协同**：RDMA 网络、NVMe SSD WAL、硬件 CRC 加速、io_uring——不浪费硬件能力。

3. **场景驱动**：OSS 大对象用大 Chunk + EC，小图片用 Super Block 合并，数据库用小 Chunk + 3 副本，AI 训练用专用通道——没有一种方案通吃所有场景。

4. **故障是常态**：从 SMART 预测到 SUSPECT 状态机，从 Scrubbing 到分优先级修复——假设任何部件随时会坏，系统依然能正常工作。

5. **持续演进**：从 GFS-like 单 Master 到 Multi-Raft 分片架构，从三副本到 EC+LRC，从 TCP 到 RDMA——每一次架构升级都回应着规模增长带来的新挑战。
