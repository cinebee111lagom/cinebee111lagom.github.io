---
title: RDMA, NCCL, InfiniBand 和 RoCE v2 — 底层细节深度解析
date: 2026-09-07 11:45:00
tags:
  - RDMA
  - NCCL
  - InfiniBand
  - RoCE
  - GPU
categories:
  - 网络
---

# RDMA, NCCL, InfiniBand & RoCE v2 — Underlying Details

# RDMA, NCCL,InfiniBand 和 RoCE v2 — 底层细节深度解析

---

## Part 1: RDMA (Remote Direct Memory Access)

# 第一部分：RDMA（远程直接内存访问）

---

### 1.1 What Is RDMA?

**RDMA** allows one computer to directly access the memory of another computer **without involving the remote CPU or operating system kernel**. This is fundamentally different from traditional TCP/IP networking.

**RDMA** 允许一台计算机直接访问另一台计算机的内存，**无需远程 CPU 或操作系统内核参与**。这与传统 TCP/IP 网络有根本区别。

### 1.2 Traditional TCP/IP vs RDMA — Data Path Comparison

```
╔══════════════════════════════════════════════════════════════════╗
║               TRADITIONAL TCP/IP STACK                           ║
║               传统 TCP/IP 协议栈                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Sender Side (Node A):                                          ║
║  发送端（节点 A）:                                                ║
║                                                                  ║
║  User Space          Kernel Space            Hardware            ║
║  用户空间             内核空间                 硬件                ║
║  ┌──────────┐     ┌──────────────────┐    ┌──────────┐          ║
║  │ App      │     │ TCP/IP Stack     │    │          │          ║
║  │ Buffer   │────▶│ ┌──────────────┐ │───▶│ NIC      │──────    ║
║  │ (user)   │copy │ │ Socket Buffer│ │copy│ TX Ring  │  wire    ║
║  └──────────┘     │ │ (sk_buff)    │ │    │ Buffer   │          ║
║       │           │ │              │ │    └──────────┘          ║
║       │           │ │ TCP header   │ │                           ║
║       │           │ │ IP header    │ │                           ║
║       │           │ │ Eth header   │ │                           ║
║       │           │ └──────────────┘ │                           ║
║       │           └──────────────────┘                           ║
║       │                                                          ║
║  copy #1           copy #2                                       ║
║  user→kernel       kernel→NIC                                    ║
║                                                                  ║
║  Total copies per send: 2+                                       ║
║  CPU involvement: HIGH (interrupts, context switches)            ║
║  每次发送的拷贝次数：2+                                           ║
║  CPU 参与度：高（中断、上下文切换）                                ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║                     RDMA DATA PATH                               ║
║                     RDMA 数据路径                                 ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  Sender Side (Node A):                                          ║
║  发送端（节点 A）:                                                ║
║                                                                  ║
║  User Space          Hardware (RNIC)                             ║
║  用户空间             硬件（RDMA 网卡）                           ║
║  ┌──────────┐      ┌──────────────────────┐                     ║
║  │ App      │      │ RDMA NIC (HCA)       │                     ║
║  │ Buffer   │─────▶│                      │──────  wire         ║
║  │ (user)   │ zero │ DMA Engine           │                     ║
║  │          │ copy │ directly reads       │                     ║
║  │ registered│     │ user memory via      │                     ║
║  │ memory   │      │ registered MR        │                     ║
║  └──────────┘      └──────────────────────┘                     ║
║       │                                                          ║
║  NO kernel involvement!                                          ║
║  无内核参与！                                                     ║
║  NO system calls during data transfer!                           ║
║  数据传输期间无系统调用！                                         ║
║  NO context switches!                                            ║
║  无上下文切换！                                                   ║
║                                                                  ║
║  Total copies: 0 (zero-copy)                                     ║
║  CPU involvement: NEAR ZERO                                      ║
║  拷贝次数：0（零拷贝）                                            ║
║  CPU 参与度：接近零                                               ║
║                                                                  ║
║  Receiver Side (Node B):                                         ║
║  接收端（节点 B）:                                                ║
║                                                                  ║
║  Hardware writes directly into registered user-space buffer      ║
║  硬件直接写入已注册的用户空间缓冲区                               ║
║  Remote CPU does NOT get interrupted                             ║
║  远程 CPU 不会被中断                                              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### 1.3 RDMA Core Concepts

#### 1.3.1 Memory Registration (MR)

Before RDMA operations can occur, memory buffers must be **registered** with the RNIC. This pins the pages in physical RAM and gives the NIC the physical addresses.

在 RDMA 操作发生之前，内存缓冲区必须向 RNIC **注册**。这会将页面锁定在物理 RAM 中，并赋予网卡物理地址。

```c
// User-space RDMA programming (libibverbs)
// 用户空间 RDMA 编程（libibverbs）

#include <infiniband/verbs.h>

// Step 1: Register memory region
// 步骤 1：注册内存区域
struct ibv_mr *mr = ibv_reg_mr(
    pd,                          // Protection Domain / 保护域
    buffer,                      // Virtual address / 虚拟地址
    buffer_size,                 // Size in bytes / 字节大小
    IBV_ACCESS_LOCAL_WRITE  |    // Allow local writes / 允许本地写
    IBV_ACCESS_REMOTE_WRITE |    // Allow remote writes / 允许远程写
    IBV_ACCESS_REMOTE_READ  |    // Allow remote reads / 允许远程读
    IBV_ACCESS_REMOTE_ATOMIC     // Allow atomic ops / 允许原子操作
);

// What happens internally during ibv_reg_mr:
// ibv_reg_mr 内部发生的事：

// 1. Kernel pins the virtual memory pages in physical RAM
//    内核将虚拟内存页面锁定在物理 RAM 中
//    (prevents swapping to disk)
//    （防止交换到磁盘）

// 2. Kernel creates a mapping: virtual → physical addresses
//    内核创建映射：虚拟地址 → 物理地址

// 3. RNIC gets the physical address list (via DMA or firmware)
//    RNIC 获取物理地址列表（通过 DMA 或固件）

// 4. A "Memory Region Key" (r_key/l_key) is generated
//    生成"内存区域密钥"（r_key/l_key）

// 5. The RNIC can now DMA-read/directly from this physical memory
//    RNIC 现在可以直接从此物理内存进行 DMA 读取

// The registered memory region:
// 已注册的内存区域：
struct ibv_mr {
    uint64_t addr;        // Virtual address / 虚拟地址
    uint32_t length;      // Size / 大小
    uint32_t lkey;        // Local key (for local operations) / 本地密钥
    uint32_t rkey;        // Remote key (given to remote side) / 远程密钥
};
```

```
Memory Registration Visualization:
内存注册可视化：

┌─────────────────────────────────────────────────────┐
│  Application Virtual Memory (User Space)            │
│  应用程序虚拟内存（用户空间）                         │
│                                                     │
│  ┌─────────────────────────────┐                    │
│  │  Registered Buffer          │ ← ibv_reg_mr()     │
│  │  Address: 0x7f3a0000        │                    │
│  │  Size: 1 GB                 │                    │
│  │  l_key: 0x1234              │                    │
│  │  r_key: 0x5678              │                    │
│  └─────────────────────────────┘                    │
└─────────────────────────────────────────────────────┘
              │ (pinned — cannot be swapped)
              │ （锁定 — 不能被交换）
              ▼
┌─────────────────────────────────────────────────────┐
│  Physical Memory (RAM)                              │
│  物理内存（RAM）                                     │
│                                                     │
│  ┌─────────────────────────────────┐                │
│  │  Physical Pages: 0x1A00000000   │                │
│  │  (contiguous or scatter-gather) │                │
│  │  Pinned by kernel               │                │
│  └─────────────────────────────────┘                │
└─────────────────────────────────────────────────────┘
              │ (physical addr table given to RNIC)
              │ （物理地址表传递给 RNIC）
              ▼
┌─────────────────────────────────────────────────────┐
│  RNIC (RDMA NIC / HCA)                              │
│  RDMA 网卡（主机通道适配器）                          │
│                                                     │
│  ┌──────────────────────────────────────┐           │
│  │  Translation Table in NIC hardware:  │           │
│  │  NIC 硬件中的转换表：                  │           │
│  │                                      │           │
│  │  r_key=0x5678 → phys=0x1A00000000   │           │
│  │                 len=1GB              │           │
│  │                 access=RW            │           │
│  └──────────────────────────────────────┘           │
│                                                     │
│  When remote node sends RDMA READ with r_key:       │
│  当远程节点使用 r_key 发送 RDMA READ 时：            │
│  NIC validates key → DMA reads memory → sends data  │
│  NIC 验证密钥 → DMA 读取内存 → 发送数据              │
│  (NO CPU involvement on either side)                 │
│  （两侧均无 CPU 参与）                               │
└─────────────────────────────────────────────────────┘
```

#### 1.3.2 Queue Pairs (QP) — The Communication Channel

RDMA uses **Queue Pairs** instead of sockets. Each QP consists of a **Send Queue (SQ)** and a **Receive Queue (RQ)**.

RDMA 使用**队列对（QP）**代替套接字。每个 QP 由一个**发送队列（SQ）**和一个**接收队列（RQ）**组成。

```
Node A                                          Node B
┌─────────────────────────┐                    ┌─────────────────────────┐
│                         │                    │                         │
│  Application            │                    │  Application            │
│  ┌─────────────┐        │                    │        ┌─────────────┐  │
│  │ Post Send   │        │                    │        │ Post Recv   │  │
│  │ (user space)│        │                    │        │ (user space)│  │
│  └──────┬──────┘        │                    │        └──────▲──────┘  │
│         │               │                    │               │         │
│         ▼               │                    │               │         │
│  ┌─────────────┐        │                    │        ┌─────────────┐  │
│  │ Send Queue  │        │                    │        │ Recv Queue  │  │
│  │ (SQ)        │        │                    │        │ (RQ)        │  │
│  │             │        │                    │        │             │  │
│  │ Work Queue  │        │                    │        │ Work Queue  │  │
│  │ Entries(WQE)│        │                    │        │ Entries(WQE)│  │
│  └──────┬──────┘        │                    │        └──────▲──────┘  │
│         │               │                    │               │         │
│         ▼               │                    │               │         │
│  ┌─────────────┐        │    RDMA Network    │        ┌─────────────┐  │
│  │ Completion  │        │   ────────────────▶│        │ Completion  │  │
│  │ Queue (CQ)  │        │                    │        │ Queue (CQ)  │  │
│  │             │        │                    │        │             │  │
│  │ CQE posted  │        │                    │        │ CQE posted  │  │
│  │ when send   │        │                    │        │ when recv   │  │
│  │ completes   │        │                    │        │ completes   │  │
│  └──────┬──────┘        │                    │        └──────▲──────┘  │
│         │               │                    │               │         │
│         ▼               │                    │               │         │
│  Poll CQ ──── done!     │                    │     done ──── Poll CQ   │
│  (user space)           │                    │           (user space)   │
│                         │                    │                         │
└─────────────────────────┘                    └─────────────────────────┘

KEY: All of this happens in USER SPACE — no kernel syscalls during data transfer!
关键：所有这些都发生在用户空间 — 数据传输期间无内核系统调用！
```

#### 1.3.3 RDMA Operations

```
┌──────────────────────────────────────────────────────────────┐
│                    RDMA Operations                            │
│                    RDMA 操作类型                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. RDMA WRITE (one-sided / 单边)                            │
│     ┌──────┐         data + r_key          ┌──────┐         │
│     │ Node ├──────────────────────────────▶│ Node │         │
│     │  A   │  Write directly into B's      │  B   │         │
│     └──────┘  registered memory            └──────┘         │
│     - Node B's CPU does NOT know it happened!               │
│     - 节点 B 的 CPU 不知道这发生了！                          │
│     - Used for: bulk data transfer, NCCL all-reduce         │
│     - 用途：批量数据传输，NCCL all-reduce                    │
│                                                              │
│  2. RDMA READ (one-sided / 单边)                             │
│     ┌──────┐         read request          ┌──────┐         │
│     │ Node │◀──────────────────────────────│ Node │         │
│     │  A   │──────────────────────────────▶│  B   │         │
│     └──────┘    data returned              └──────┘         │
│     - Node B's CPU does NOT know it happened!               │
│     - 节点 B 的 CPU 不知道这发生了！                          │
│     - Used for: fetching remote model shards                │
│     - 用途：获取远程模型分片                                  │
│                                                              │
│  3. SEND/RECV (two-sided / 双边)                             │
│     ┌──────┐         message               ┌──────┐         │
│     │ Node ├──────────────────────────────▶│ Node │         │
│     │  A   │  Must have pre-posted recv    │  B   │         │
│     └──────┘  buffer on receiver           └──────┘         │
│     - Requires receiver to pre-post a receive buffer        │
│     - 需要接收方预先发布接收缓冲区                            │
│     - Used for: control messages, small transfers           │
│     - 用途：控制消息，小数据传输                              │
│                                                              │
│  4. RDMA ATOMIC (one-sided / 单边)                           │
│     ┌──────┐    compare-and-swap or        ┌──────┐         │
│     │ Node ├──────────────────────────────▶│ Node │         │
│     │  A   │◀──────────────────────────────│  B   │         │
│     └──────┘    fetch-and-add              └──────┘         │
│     - Atomic read-modify-write on remote memory             │
│     - 远程内存的原子读-修改-写                                │
│     - Used for: distributed locks, synchronization          │
│     - 用途：分布式锁，同步                                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 1.4 RDMA Verbs — The Complete Send/Receive Flow

```
Detailed steps for an RDMA SEND operation:
RDMA SEND 操作的详细步骤：

SENDER (Node A):                          RECEIVER (Node B):
发送端（节点 A）                           接收端（节点 B）

[1] ibv_reg_mr(buffer)                     [1] ibv_reg_mr(recv_buf)
    Register memory / 注册内存                 Register memory / 注册内存

[2] ibv_post_recv(qp, wr)                  [2] ibv_post_recv(qp, wr)
                                               Pre-post receive buffer
                                               预先发布接收缓冲区

[3] ibv_post_send(qp, wr) ◄─────────────── Must happen AFTER receiver
    Post send work request                  posts recv
    发布发送工作请求

[4] RNIC reads WQE from SQ                 [4] (waiting — no CPU involvement)
    RNIC 从 SQ 读取 WQE

[5] RNIC DMA-reads buffer data             [5] RNIC matches incoming
    from registered memory                      packet to pre-posted
    RNIC 从注册内存 DMA 读取缓冲区数据             recv WQE

[6] RNIC constructs packet:                [6] RNIC DMA-writes data into
    - BTH (Base Transport Header)               receiver's registered buffer
    - Payload                                   RNIC 将数据 DMA 写入接收方
    - ICRC (Invariant CRC)                      的注册缓冲区

[7] RNIC transmits packet over wire
    RNIC 在链路上传输数据包

[8] RNIC posts CQE to CQ                   [7] RNIC posts CQE to CQ
    (send complete)                             (receive complete)
    RNIC 向 CQ 发布完成队列条目                 RNIC 向 CQ 发布完成队列条目

[9] App polls CQ → sees completion         [8] App polls CQ → sees completion
    应用程序轮询 CQ → 看到完成                   应用程序轮询 CQ → 看到完成
    (user space, no syscall!)                   (user space, no syscall!)
    （用户空间，无系统调用！）                     （用户空间，无系统调用！）

CPU involvement: ~0% during data transfer
CPU 在数据传输期间的参与：约 0%
```

### 1.5 RDMA Transport Types

```
┌──────────────────────────────────────────────────────────────┐
│                  RDMA Transport Types                         │
│                  RDMA 传输类型                                 │
├──────────┬──────────────────┬────────────────────────────────┤
│ Type     │ Reliability      │ Use Case                       │
│ 类型     │ 可靠性           │ 用途                            │
├──────────┼──────────────────┼────────────────────────────────┤
│ RC       │ Reliable         │ TCP-like, ordered delivery     │
│ (Reliable│ Connected        │ 可靠连接，有序传递              │
│ Connected)│ 1 QP per pair    │ NCCL uses this most           │
│          │                  │ NCCL 最常使用                   │
├──────────┼──────────────────┼────────────────────────────────┤
│ UC       │ Unreliable       │ Datagram-like, no ACK          │
│ (Unreliable│ Connected       │ 类似数据报，无确认              │
│ Connected)│                  │ Streaming video / 流媒体       │
├──────────┼──────────────────┼────────────────────────────────┤
│ UD       │ Unreliable       │ One-to-many, max 4KB payload   │
│ (Unreliable│ Datagram        │ 一对多，最大 4KB 载荷           │
│ Datagram)│                  │ Multicast / 组播               │
└──────────┴──────────────────┴────────────────────────────────┘

NCCL primarily uses RC (Reliable Connected) for:
NCCL 主要使用 RC（可靠连接）用于：
- All-reduce gradients
  All-reduce 梯度
- All-gather model weights
  All-gather 模型权重
- Point-to-point tensor transfers
  点对点张量传输
```

---

## Part 2: InfiniBand

# 第二部分：InfiniBand

---

### 2.1 InfiniBand Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    InfiniBand Architecture                        │
│                    InfiniBand 体系结构                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    SOFTWARE LAYER                         │    │
│  │                    软件层                                  │    │
│  │                                                          │    │
│  │  User Space:                                             │    │
│  │  用户空间:                                                │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │    │
│  │  │ NCCL     │  │ MPI      │  │ App      │               │    │
│  │  │ (AI/ML)  │  │ (HPC)    │  │ (direct) │               │    │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘               │    │
│  │       │              │              │                     │    │
│  │       ▼              ▼              ▼                     │    │
│  │  ┌──────────────────────────────────────────┐            │    │
│  │  │         libibverbs (Verbs API)           │            │    │
│  │  │         (用户空间驱动库)                   │            │    │
│  │  └──────────────────┬───────────────────────┘            │    │
│  │                     │                                    │    │
│  │  Kernel Space:      │ (only for setup, NOT data xfer)   │    │
│  │  内核空间:           │ （仅用于建立连接，非数据传输）       │    │
│  │  ┌──────────────────┴───────────────────────┐            │    │
│  │  │         IB Core Kernel Module            │            │    │
│  │  │         (IB 核心内核模块)                  │            │    │
│  │  │  - Memory registration                   │            │    │
│  │  │  - QP creation                           │            │    │
│  │  │  - Protection domain management          │            │    │
│  │  └──────────────────────────────────────────┘            │    │
│  └──────────────────────────────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    HARDWARE LAYER                         │    │
│  │                    硬件层                                  │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────┐        │    │
│  │  │  HCA (Host Channel Adapter)                  │        │    │
│  │  │  主机通道适配器                                │        │    │
│  │  │                                              │        │    │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐     │        │    │
│  │  │  │ QP 0     │ │ QP 1     │ │ QP N     │     │        │    │
│  │  │  │ SQ + RQ  │ │ SQ + RQ  │ │ SQ + RQ  │     │        │    │
│  │  │  └──────────┘ └──────────┘ └──────────┘     │        │    │
│  │  │                                              │        │    │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐     │        │    │
│  │  │  │ CQ 0     │ │ CQ 1     │ │ CQ N     │     │        │    │
│  │  │  └──────────┘ └──────────┘ └──────────┘     │        │    │
│  │  │                                              │        │    │
│  │  │  ┌──────────────────────────────────────┐    │        │    │
│  │  │  │ DMA Engine / RDMA Engine              │    │        │    │
│  │  │  │ (硬件加速：零拷贝、校验和)             │    │        │    │
│  │  │  └──────────────────────────────────────┘    │        │    │
│  │  │                                              │        │    │
│  │  │  ┌──────────────────────────────────────┐    │        │    │
│  │  │  │ Network Processor / Embedded CPU      │    │        │    │
│  │  │  │ (transport protocol offload)          │    │        │    │
│  │  │  │ 传输协议卸载到硬件                     │    │        │    │
│  │  │  └──────────────────────────────────────┘    │        │    │
│  │  └──────────────────────────────────────────────┘        │    │
│  │                         │                                 │    │
│  │                    InfiniBand Link                        │    │
│  │                    (copper or optical)                    │    │
│  │                    InfiniBand 链路（铜缆或光纤）           │    │
│  └──────────────────────────────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    NETWORK LAYER                          │    │
│  │                    网络层                                  │    │
│  │                                                          │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │    │
│  │  │ Switch      │───▶│ Switch      │───▶│ Switch      │   │    │
│  │  │ (Leaf/ToR)  │    │ (Spine)     │    │ (Leaf/ToR)  │   │    │
│  │  │             │    │             │    │             │   │    │
│  │  │ Subnet      │    │             │    │             │   │    │
│  │  │ Manager runs│    │             │    │             │   │    │
│  │  │ here        │    │             │    │             │   │    │
│  │  └─────────────┘    └─────────────┘    └─────────────┘   │    │
│  │                                                          │    │
│  │  InfiniBand uses LID (Local ID) + GID (Global ID)       │    │
│  │  InfiniBand 使用 LID（本地 ID）+ GID（全局 ID）          │    │
│  │  routing, NOT IP addresses!                              │    │
│  │  路由，而非 IP 地址！                                     │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 InfiniBand Speed Generations

```
┌─────────────┬──────────────┬───────────────┬────────────────────┐
│ Generation  │ Speed        │ Per-Lane BW   │ Typical Link Width │
│ 代次        │ 速度         │ 每通道带宽     │ 典型链路宽度        │
├─────────────┼──────────────┼───────────────┼────────────────────┤
│ SDR         │ 2.5 Gbps     │ 2.5 Gbps      │ 4x = 10 Gbps      │
│ DDR         │ 5 Gbps       │ 5 Gbps        │ 4x = 20 Gbps      │
│ QDR         │ 10 Gbps      │ 10 Gbps       │ 4x = 40 Gbps      │
│ FDR         │ 14.0625 Gbps │ 14.0625 Gbps  │ 4x = 56.25 Gbps   │
│ EDR         │ 25.78125 Gbps│ 25.78125 Gbps │ 4x = 100 Gbps     │
│ HDR         │ 50 Gbps      │ 50 Gbps       │ 4x = 200 Gbps     │
│ NDR         │ 100 Gbps     │ 100 Gbps      │ 4x = 400 Gbps     │
│ XDR (2025+) │ 200 Gbps     │ 200 Gbps      │ 4x = 800 Gbps     │
└─────────────┴──────────────┴───────────────┴────────────────────┘

Current AI clusters typically use HDR (200 Gbps) or NDR (400 Gbps)
当前 AI 集群通常使用 HDR（200 Gbps）或 NDR（400 Gbps）

Example: NVIDIA DGX H100 uses 8× NDR 400Gbps InfiniBand = 3.2 Tbps total
示例：NVIDIA DGX H100 使用 8× NDR 400Gbps InfiniBand = 总计 3.2 Tbps
```

### 2.3 InfiniBand Subnet Manager (SM)

```
InfiniBand requires a Subnet Manager — unique among high-speed fabrics:
InfiniBand 需要子网管理器 — 这在高速网络中是独特的：

┌────────────────────────────────────────────────────────┐
│                   Subnet Manager                        │
│                   子网管理器                             │
├────────────────────────────────────────────────────────┤
│                                                        │
│  On startup / topology change:                         │
│  启动时 / 拓扑变更时：                                  │
│                                                        │
│  1. SM discovers all nodes and switches                │
│     SM 发现所有节点和交换机                             │
│     (sends SMP — Subnet Management Packets)            │
│     （发送 SMP — 子网管理数据包）                        │
│                                                        │
│  2. SM assigns LIDs to every port                      │
│     SM 为每个端口分配 LID                               │
│     LID = Local Identifier (like a MAC, but for IB)    │
│     LID = 本地标识符（类似 MAC，但用于 InfiniBand）      │
│                                                        │
│  3. SM computes routing tables                         │
│     SM 计算路由表                                       │
│     - LFT (Linear Forwarding Table) per switch         │
│       每个交换机的 LFT（线性转发表）                     │
│     - Optimized for: minimal hops, load balancing      │
│       优化目标：最少跳数、负载均衡                       │
│                                                        │
│  4. SM programs forwarding tables into switches        │
│     SM 将转发表写入交换机                               │
│                                                        │
│  5. SM runs continuously for fault management          │
│     SM 持续运行以进行故障管理                           │
│     - If link fails → reroutes                         │
│       如果链路故障 → 重新路由                           │
│     - Typical failover time: < 1 second                │
│       典型故障转移时间：< 1 秒                          │
│                                                        │
│  Typical SM: OpenSM (open source) or NVIDIA UFM        │
│  典型 SM：OpenSM（开源）或 NVIDIA UFM                   │
└────────────────────────────────────────────────────────┘
```

### 2.4 InfiniBand Packet Structure

```
InfiniBand Packet (at Link Layer):
InfiniBand 数据包（链路层）：

┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ ┌────────┐  │
│  │ Local    │ │ Packet   │ │ Base     │ │      │ │        │  │
│  │ Route    │ │ Sequence │ │ Transport│ │ Data │ │ ICRC   │  │
│  │ Header   │ │ Number   │ │ Header   │ │(MTU) │ │        │  │
│  │ (LRH)    │ │ (PSN)    │ │ (BTH)    │ │      │ │        │  │
│  │ 8 bytes  │ │          │ │ 12 bytes │ │      │ │4 bytes │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────┘ └────────┘  │
│                                                                │
│  LRH contains:                                                 │
│  LRH 包含：                                                    │
│  - DLID (Destination LID) — where to go                        │
│    目标 LID — 去哪里                                            │
│  - SLID (Source LID) — where it came from                      │
│    源 LID — 从哪来                                              │
│  - VL (Virtual Lane) — for QoS / congestion avoidance          │
│    虚拟通道 — 用于 QoS / 拥塞避免                               │
│  - LNH (Link Next Header)                                      │
│                                                                │
│  BTH contains:                                                 │
│  BTH 包含：                                                    │
│  - OpCode (SEND, RDMA_WRITE, RDMA_READ, etc.)                 │
│    操作码（SEND、RDMA_WRITE、RDMA_READ 等）                     │
│  - Destination QP number                                       │
│    目标 QP 编号                                                 │
│  - Partition Key (P_Key)                                       │
│    分区密钥                                                     │
│  - Solicited Event bit                                         │
│    请求事件位                                                   │
│                                                                │
│  MTU sizes: 256 / 512 / 1024 / 2048 / 4096 bytes              │
│  MTU 大小：256 / 512 / 1024 / 2048 / 4096 字节                │
│  (InfiniBand MTU, NOT Ethernet MTU!)                           │
│  （InfiniBand MTU，非以太网 MTU！）                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Part 3: RoCE v2 (RDMA over Converged Ethernet v2)

# 第三部分：RoCE v2（基于融合以太网的 RDMA v2）

---

### 3.1 What Is RoCE v2?

RoCE v2 allows RDMA operations to run over **standard Ethernet/UDP/IP networks** instead of InfiniBand fabric. This is critical because many data centers already have Ethernet infrastructure.

RoCE v2 允许 RDMA 操作在**标准以太网/UDP/IP 网络**上运行，而非 InfiniBand 基础设施。这非常重要，因为许多数据中心已经拥有以太网基础设施。

### 3.2 RoCE v2 Packet Encapsulation

```
┌────────────────────────────────────────────────────────────────────┐
│              RoCE v2 Packet Encapsulation                          │
│              RoCE v2 数据包封装                                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┬────────┐│
│  │ Ethernet │ IP       │ UDP      │ BTH      │ Payload  │ ICRC   ││
│  │ Header   │ Header   │ Header   │ (IB      │ (up to   │        ││
│  │ 14 bytes │ 20 bytes │ 8 bytes  │ Transport)│ 4096 B) │4 bytes ││
│  └──────────┴──────────┴──────────┴──────────┴──────────┴────────┘│
│                                                                    │
│  Ethernet Header:                                                  │
│  以太网头部：                                                        │
│  - Dst MAC: next hop MAC                                           │
│    目标 MAC：下一跳 MAC                                              │
│  - Src MAC: local NIC MAC                                          │
│    源 MAC：本地网卡 MAC                                              │
│  - EtherType: 0x0800 (IPv4)                                        │
│                                                                    │
│  IP Header:                                                        │
│  IP 头部：                                                          │
│  - Src IP: 192.168.1.10                                            │
│  - Dst IP: 192.168.1.11                                            │
│  - Protocol: 17 (UDP)                                              │
│  - DSCP: 26 (recommended for lossless)                             │
│    DSCP：26（推荐用于无损网络）                                       │
│  - ECN bits: for congestion notification                            │
│    ECN 位：用于拥塞通知                                              │
│                                                                    │
│  UDP Header:                                                       │
│  UDP 头部：                                                         │
│  - Src Port: QP number (encoded)                                   │
│    源端口：QP 编号（编码）                                            │
│  - Dst Port: 4791 (standard RoCE v2 destination port)              │
│    目标端口：4791（标准 RoCE v2 目标端口）                            │
│                                                                    │
│  BTH (Base Transport Header):                                      │
│  BTH（基本传输头部）：                                               │
│  - Same as InfiniBand BTH                                          │
│    与 InfiniBand BTH 相同                                           │
│  - OpCode, QP number, PSN, etc.                                    │
│    操作码、QP 编号、PSN 等                                           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

Key difference from InfiniBand:
与 InfiniBand 的关键区别：

InfiniBand:  [LRH][BTH][Payload][ICRC]        ← Native IB headers
             使用原生 IB 头部

RoCE v2:     [Eth][IP][UDP][BTH][Payload][ICRC] ← Encapsulated in UDP/IP
             封装在 UDP/IP 中

This means RoCE v2 runs over ANY IP-routed Ethernet network!
这意味着 RoCE v2 可以在任何 IP 路由的以太网网络上运行！
```

### 3.3 Lossless Ethernet Requirements — PFC & ECN

Standard Ethernet is **lossy** — it drops packets on congestion. RDMA requires **lossless** delivery. RoCE v2 solves this with two mechanisms:

标准以太网是**有损的** — 拥塞时丢弃数据包。RDMA 需要**无损**传递。RoCE v2 通过两种机制解决这个问题：

#### 3.3.1 PFC (Priority Flow Control) — IEEE 802.1Qbb

```
PFC operates at Layer 2 — per-priority pause:
PFC 在第 2 层运行 — 按优先级暂停：

┌─────────────────────────────────────────────────────────┐
│                    PFC Mechanism                         │
│                    PFC 机制                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Without PFC:                                           │
│  无 PFC：                                                │
│                                                         │
│  Sender ──────────▶ [Switch Buffer FULL] ──X──▶ DROP    │
│  发送端              [交换机缓冲区满]        丢弃         │
│                                                         │
│  With PFC:                                              │
│  有 PFC：                                                │
│                                                         │
│  Sender ──────────▶ [Switch Buffer FILLING]              │
│  发送端              [交换机缓冲区填充中]                  │
│      ▲                      │                            │
│      │                      ▼ (buffer reaches 80%)      │
│      │              [Switch sends PFC PAUSE frame]       │
│      │              [交换机发送 PFC PAUSE 帧]             │
│      │                      │                            │
│      │                      ▼                            │
│      └──────────── [Sender STOPS transmitting]           │
│                     [发送端停止传输]                       │
│                                                         │
│  PFC PAUSE Frame:                                       │
│  PFC PAUSE 帧：                                          │
│  ┌─────────────────────────────────────────────┐        │
│  │ Dst MAC: 01:80:C2:00:00:01 (reserved)       │        │
│  │ EtherType: 0x8808                            │        │
│  │ Opcode: 0x0101 (PFC)                         │        │
│  │ Priority Bitmap: which priorities to pause    │        │
│  │ 优先级位图：暂停哪些优先级                      │        │
│  │ Timers: how long to pause per priority        │        │
│  │ 定时器：每个优先级暂停多长时间                  │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  In practice: RDMA traffic uses Priority 3 (or 4)       │
│  实际中：RDMA 流量使用优先级 3（或 4）                     │
│  Data traffic uses other priorities                      │
│  数据流量使用其他优先级                                    │
│  → PFC only pauses RDMA traffic, not data traffic        │
│    PFC 仅暂停 RDMA 流量，不暂停数据流量                    │
│                                                         │
└─────────────────────────────────────────────────────────┘

PFC PROBLEM: "Pause Storms"
PFC 问题："暂停风暴"

┌───────────────────────────────────────────────┐
│                                               │
│  If congestion propagates across switches:    │
│  如果拥塞在交换机之间传播：                     │
│                                               │
│  Node A → SW1 → SW2 → SW3 → Node B           │
│           ▲              │                    │
│           └── PFC PAUSE ─┘                    │
│                                               │
│  PFC pauses propagate backward:               │
│  PFC 暂停向后传播：                            │
│  SW3 PAUSE → SW2 PAUSE → SW1 PAUSE → Node A  │
│                                               │
│  This can pause the ENTIRE network!           │
│  这可能暂停整个网络！                           │
│  Head-of-line blocking affects all traffic    │
│  队头阻塞影响所有流量                           │
│                                               │
└───────────────────────────────────────────────┘
```

#### 3.3.2 ECN (Explicit Congestion Notification)

```
ECN operates at Layer 3 — end-to-end congestion signaling:
ECN 在第 3 层运行 — 端到端拥塞信号：

┌─────────────────────────────────────────────────────────────┐
│                    ECN Mechanism                             │
│                    ECN 机制                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: IP header ECN bits set by sender                   │
│  步骤 1：发送端设置 IP 头部 ECN 位                             │
│                                                             │
│  ┌───────────────┐                                          │
│  │ IP Header     │                                          │
│  │ ECN field:    │                                          │
│  │ ┌───┬───┐     │                                          │
│  │ │ECT│ECT│     │  00 = Not ECN-capable                   │
│  │ │ 0 │ 1 │     │  01 = ECT(1) — ECN capable              │
│  │ └───┴───┘     │  10 = ECT(0) — ECN capable              │
│  │               │  11 = CE (Congestion Experienced)        │
│  └───────────────┘                                          │
│                                                             │
│  Step 2: Switch detects congestion (queue depth threshold)  │
│  步骤 2：交换机检测到拥塞（队列深度阈值）                      │
│                                                             │
│  ┌────────────┐         ┌────────────┐                      │
│  │ Packet in  │────────▶│ Switch     │                      │
│  │ ECN=01     │         │ Queue      │                      │
│  └────────────┘         │ Depth >    │                      │
│                         │ threshold! │                      │
│                         └─────┬──────┘                      │
│                               │                             │
│                    Switch sets ECN=11 (CE)                   │
│                    交换机设置 ECN=11（CE）                    │
│                               │                             │
│                               ▼                             │
│                         ┌────────────┐                      │
│                         │ Packet out │                      │
│                         │ ECN=11 (CE)│                      │
│                         └────────────┘                      │
│                                                             │
│  Step 3: Receiver sees ECN=CE, sends CNP (Congestion        │
│          Notification Packet) back to sender                 │
│  步骤 3：接收端看到 ECN=CE，向发送端发送 CNP（拥塞通知包）     │
│                                                             │
│  ┌────────────┐   CNP    ┌────────────┐                     │
│  │ Receiver   │◀────────│ Receiver   │                     │
│  │ Node B     │ (UDP)    │ generates  │                     │
│  └─────┬──────┘          └────────────┘                     │
│        │                                                   │
│        ▼                                                   │
│  ┌────────────┐                                            │
│  │ Sender     │                                            │
│  │ Node A     │ ← reduces send rate                        │
│  │            │   降低发送速率                               │
│  └────────────┘                                            │
│                                                             │
│  This is SLOWER but SAFER than PFC                          │
│  这比 PFC 更慢但更安全                                       │
│  No pause storms!                                           │
│  没有暂停风暴！                                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 RoCE v2 vs InfiniBand — Detailed Comparison

```
┌─────────────────────┬────────────────────┬────────────────────┐
│ Feature             │ InfiniBand         │ RoCE v2            │
│ 特性                │ InfiniBand         │ RoCE v2            │
├─────────────────────┼────────────────────┼────────────────────┤
│ Physical Layer      │ IB cables          │ Ethernet cables    │
│ 物理层              │ IB 线缆             │ 以太网线缆          │
│                     │ (QSFP, SFP+)       │ (same transceivers)│
├─────────────────────┼────────────────────┼────────────────────┤
│ Network Layer       │ LID-based routing  │ IP-based routing   │
│ 网络层              │ 基于 LID 路由       │ 基于 IP 路由        │
├─────────────────────┼────────────────────┼────────────────────┤
│ Switching           │ IB switches        │ Ethernet switches  │
│ 交换                │ IB 交换机           │ 以太网交换机        │
│                     │ (Mellanox/NVIDIA)  │ (any vendor)       │
├─────────────────────┼────────────────────┼────────────────────┤
│ Congestion Control  │ Credit-based       │ PFC + ECN          │
│ 拥塞控制            │ 基于信用            │ PFC + ECN           │
│                     │ (inherent)         │ (must configure)   │
├─────────────────────┼────────────────────┼────────────────────┤
│ Reliability         │ Hardware CRC +     │ ICRC + retransmit  │
│ 可靠性              │ retransmit         │ (soft/hard)        │
│                     │ 硬件 CRC + 重传    │ ICRC + 重传         │
├─────────────────────┼────────────────────┼────────────────────┤
│ Latency             │ ~0.6 μs            │ ~1.5 μs            │
│ 延迟                │ ~0.6 微秒           │ ~1.5 微秒           │
│ (node-to-node)      │ (节点到节点)        │ (节点到节点)        │
├─────────────────────┼────────────────────┼────────────────────┤
│ Subnet Manager      │ Required           │ Not needed (IP)    │
│ 子网管理器          │ 必需                │ 不需要（IP 协议）    │
├─────────────────────┼────────────────────┼────────────────────┤
│ Multi-path          │ SH/LID MC groups   │ IP ECMP            │
│ 多路径              │ SH/LID MC 组       │ IP ECMP             │
├─────────────────────┼────────────────────┼────────────────────┤
│ Cost                │ Higher             │ Lower              │
│ 成本                │ 较高                │ 较低                │
│                     │ (specialized HW)   │ (commodity HW)     │
├─────────────────────┼────────────────────┼────────────────────┤
│ Ecosystem           │ NVIDIA-dominant    │ Multi-vendor       │
│ 生态系统            │ NVIDIA 主导         │ 多供应商            │
├─────────────────────┼────────────────────┼────────────────────┤
│ AI/ML Adoption      │ Very high          │ Growing fast       │
│ AI/ML 采用率        │ 非常高              │ 快速增长            │
│                     │ (default for DGX)  │ (public clouds)    │
└─────────────────────┴────────────────────┴────────────────────┘
```

---

## Part 4: NCCL (NVIDIA Collective Communications Library)

# 第四部分：NCCL（NVIDIA 集合通信库）

---

### 4.1 What Is NCCL?

NCCL is NVIDIA's library for **multi-GPU and multi-node collective operations**. It is the backbone of distributed AI training and inference.

NCCL 是 NVIDIA 的**多 GPU 和多节点集合操作**库。它是分布式 AI 训练和推理的骨干。

### 4.2 NCCL Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    NCCL Architecture                              │
│                    NCCL 体系结构                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  Application Layer                          │  │
│  │                  应用层                                      │  │
│  │                                                            │  │
│  │   PyTorch          TensorFlow       Custom App             │  │
│  │   torch.distributed tf.distribute    直接调用 NCCL API      │  │
│  │        │                  │                │                │  │
│  │        ▼                  ▼                ▼                │  │
│  │   ┌──────────────────────────────────────────────┐         │  │
│  │   │           NCCL C API                         │         │  │
│  │   │                                              │         │  │
│  │   │  ncclAllReduce()    ← Most important for     │         │  │
│  │   │  ncclAllGather()       distributed training  │         │  │
│  │   │  ncclReduceScatter()  分布式训练最重要的操作  │         │  │
│  │   │  ncclBroadcast()                              │         │  │
│  │   │  ncclSend() / ncclRecv()                     │         │  │
│  │   └──────────────────────┬───────────────────────┘         │  │
│  └──────────────────────────┼────────────────────────────────┘  │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              NCCL Runtime Core                            │    │
│  │              NCCL 运行时核心                                │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │         Proxy Thread (per connection)             │    │    │
│  │  │         代理线程（每个连接一个）                    │    │    │
│  │  │                                                  │    │    │
│  │  │  Manages data movement between:                  │    │    │
│  │  │  管理以下之间的数据移动：                           │    │    │
│  │  │  - GPU memory ↔ System memory (via PCIe/NVLink)  │    │    │
│  │  │  - GPU 内存 ↔ 系统内存（通过 PCIe/NVLink）        │    │    │
│  │  │  - System memory ↔ Network (via RDMA/TCP)        │    │    │
│  │  │  - 系统内存 ↔ 网络（通过 RDMA/TCP）               │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  │                                                          │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │         Channels (Ring, Tree, NVLS)               │    │    │
│  │  │         通道（环形、树形、NVLS）                    │    │    │
│  │  │                                                  │    │    │
│  │  │  NCCL creates multiple channels for parallelism   │    │    │
│  │  │  NCCL 创建多个通道以实现并行化                      │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Transport Layer (Plugins)                    │    │
│  │              传输层（插件）                                 │    │
│  │                                                          │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │    │
│  │  │ P2P        │ │ SHARP      │ │ NET        │            │    │
│  │  │ (NVLink/   │ │ (In-Band   │ │ (RDMA/     │            │    │
│  │  │  PCIe)     │ │  Reduction)│ │  TCP/Socket)│            │    │
│  │  │            │ │            │ │            │            │    │
│  │  │ GPU-to-GPU │ │ Switch-level│ │ Node-to-  │            │    │
│  │  │ same node  │ │ reduction  │ │ node       │            │    │
│  │  │ 同节点     │ │ 交换机级归约│ │ 跨节点     │            │    │
│  │  │ GPU 间通信 │ │            │ │ 节点间通信  │            │    │
│  │  └────────────┘ └────────────┘ └────────────┘            │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              Hardware Layer                               │    │
│  │              硬件层                                        │    │
│  │                                                          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │    │
│  │  │ NVLink   │  │ PCIe     │  │ InfiniBand│  │ RoCE v2  │ │    │
│  │  │ Switch   │  │ Bus      │  │ HCA      │  │ NIC      │ │    │
│  │  │ 900 GB/s │  │ 64 GB/s  │  │ 400 Gbps │  │ 100 Gbps │ │    │
│  │  │ (NVSwitch│  │ (Gen5 x16│  │ (NDR)    │  │          │ │    │
│  │  │  per DGX)│  │  per GPU)│  │          │  │          │ │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3 NCCL Initialization — How It Discovers Topology

```
When a PyTorch distributed process starts:
当 PyTorch 分布式进程启动时：

[1] torch.distributed.init_process_group("nccl")
         │
         ▼
[2] NCCL reads environment variables:
    NCCL 读取环境变量：
    - NCCL_COMM_ID=192.168.1.10:12345  (bootstrap address)
    - NCCL_SOCKET_IFNAME=eth0           (network interface)
    - NCCL_IB_DISABLE=0                 (enable IB)
    - NCCL_P2P_DISABLE=0                (enable NVLink P2P)
         │
         ▼
[3] NCCL Bootstrap Phase (ring/rail discovery):
    NCCL 引导阶段（环/轨道发现）：

    Process rank 0 acts as "bootstrap root"
    进程 rank 0 充当"引导根节点"
    
    All processes connect to rank 0 via TCP socket
    所有进程通过 TCP 套接字连接到 rank 0
    
    Rank 0 collects all: rank, hostname, GPU index, 
                          PCI bus ID, IB HCA port info
    Rank 0 收集所有：rank、主机名、GPU 索引、
                     PCI 总线 ID、IB HCA 端口信息
         │
         ▼
[4] NCCL Topology Detection:
    NCCL 拓扑检测：

    For each GPU pair, NCCL checks:
    对于每对 GPU，NCCL 检查：

    ┌─────────────────────────────────────────────────┐
    │  Detection Order (fastest to slowest):           │
    │  检测顺序（从最快到最慢）：                        │
    │                                                  │
    │  1. NVLink/NVSwitch direct connection?           │
    │     NVLink/NVSwitch 直接连接？                   │
    │     → Use P2P transport (900 GB/s)              │
    │       使用 P2P 传输（900 GB/s）                   │
    │                                                  │
    │  2. PCIe peer-to-peer (same node)?              │
    │     PCIe 点对点（同节点）？                       │
    │     → Use P2P transport (64 GB/s)               │
    │       使用 P2P 传输（64 GB/s）                    │
    │                                                  │
    │  3. Same node, no P2P? → Use SHM (shared mem)   │
    │     同节点，无 P2P？→ 使用 SHM（共享内存）        │
    │                                                  │
    │  4. Different node, IB available?                │
    │     不同节点，IB 可用？                           │
    │     → Use IB transport (400 Gbps)               │
    │       使用 IB 传输（400 Gbps）                    │
    │                                                  │
    │  5. Different node, RoCE available?              │
    │     不同节点，RoCE 可用？                         │
    │     → Use NET/RDMA transport (100 Gbps)         │
    │       使用 NET/RDMA 传输（100 Gbps）              │
    │                                                  │
    │  6. Fallback: TCP/Socket                         │
    │     回退：TCP/Socket                              │
    │     → Use Socket transport (slowest)            │
    │       使用 Socket 传输（最慢）                    │
    └─────────────────────────────────────────────────┘
         │
         ▼
[5] NCCL builds logical topology rings/trees:
    NCCL 构建逻辑拓扑环/树：

    Example for 8 GPUs across 2 nodes:
    8 个 GPU 跨 2 个节点的示例：

    Ring:  GPU0(A)→GPU1(A)→GPU2(A)→GPU3(A)→
           GPU4(B)→GPU5(B)→GPU6(B)→GPU7(B)→GPU0(A)
    
    Tree:  Root at GPU0(A) and GPU4(B)
           branching to local GPUs and cross-node
         │
         ▼
[6] NCCL allocates buffers and creates proxy threads:
    NCCL 分配缓冲区并创建代理线程：

    For each channel × each connection:
    对于每个通道 × 每个连接：
    - Allocate send/recv buffers (CUDA pinned memory)
      分配发送/接收缓冲区（CUDA 固定内存）
    - Create proxy thread for async data movement
      创建代理线程进行异步数据移动
    - For RDMA: register buffers with ibv_reg_mr
      对于 RDMA：使用 ibv_reg_mr 注册缓冲区
         │
         ▼
[7] NCCL connection established — ready for collectives!
    NCCL 连接建立 — 准备执行集合操作！
```

### 4.4 NCCL All-Reduce — The Most Important Operation

```
All-Reduce: compute sum of tensors across all GPUs, 
            result available on all GPUs
All-Reduce：计算所有 GPU 上张量的和，结果在所有 GPU 上可用
Used for: gradient synchronization in distributed training
用于：分布式训练中的梯度同步

NCCL uses Ring All-Reduce (default algorithm):
NCCL 使用环形 All-Reduce（默认算法）：

Step 1: Reduce-Scatter (N-1 steps)
步骤 1：Reduce-Scatter（N-1 步）

    GPU 0    GPU 1    GPU 2    GPU 3
    [A|B|C|D][A|B|C|D][A|B|C|D][A|B|C|D]  ← each GPU has full tensor
                                              每个 GPU 都有完整张量
    
    Step 1: Each GPU sends chunk to next, receives from prev
    步骤 1：每个 GPU 发送块到下一个，从上一个接收
    
    GPU 0    GPU 1    GPU 2    GPU 3
    [  |B+ |  |    ][    |   |  |D+ ]    += means accumulated
    [A |  |C |D   ][A   |B  |C |   ]    += 表示累积
    
    ... (N-1 steps for 4 GPUs = 3 steps)
    ...（4 个 GPU 的 N-1 步 = 3 步）
    
    After Reduce-Scatter:
    Reduce-Scatter 后：
    GPU 0: [sum_A| |  |  ]  ← only chunk A is complete
    GPU 1: [  |sum_B|  |  ]     只有块 A 是完整的
    GPU 2: [  |  |sum_C|  ]
    GPU 3: [  |  |  |sum_D]


Step 2: All-Gather (N-1 steps)
步骤 2：All-Gather（N-1 步）

    GPU 0 broadcasts sum_A to all others via ring
    GPU 0 通过环向所有其他 GPU 广播 sum_A
    
    After All-Gather:
    All-Gather 后：
    GPU 0: [sum_A|sum_B|sum_C|sum_D]  ← FULL result!
    GPU 1: [sum_A|sum_B|sum_C|sum_D]  ← FULL result!
    GPU 2: [sum_A|sum_B|sum_C|sum_D]  ← FULL result!
    GPU 3: [sum_A|sum_B|sum_C|sum_D]  ← FULL result!
                                        完整结果！


Bandwidth Analysis:
带宽分析：

Total data transferred per GPU:
每个 GPU 传输的总数据量：

  Reduce-Scatter: (N-1)/N × tensor_size
  All-Gather:     (N-1)/N × tensor_size
  
  Total: 2 × (N-1)/N × tensor_size
  
  For large N → approaches 2 × tensor_size (optimal)
  对于大 N → 接近 2 × tensor_size（最优）

This is bandwidth-optimal!
这是带宽最优的！
```

### 4.5 NCCL Communication Channels — Ring vs Tree vs NVLS

```
┌──────────────────────────────────────────────────────────────┐
│                 NCCL Algorithms                               │
│                 NCCL 算法                                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. RING (Default)                                           │
│     环形（默认）                                               │
│                                                              │
│     GPU0 ──▶ GPU1 ──▶ GPU2 ──▶ GPU3 ──▶ GPU0               │
│     (each GPU has 1 send + 1 recv at a time)                │
│     （每个 GPU 同时有 1 个发送 + 1 个接收）                    │
│                                                              │
│     Pros: bandwidth-optimal for large messages               │
│     优点：大消息时带宽最优                                     │
│     Cons: latency scales with N (N-1 steps)                  │
│     缺点：延迟随 N 扩展（N-1 步）                             │
│                                                              │
│  2. TREE (Latency-optimized)                                 │
│     树形（延迟优化）                                           │
│                                                              │
│              GPU0                                            │
│             /    \                                           │
│          GPU1    GPU2                                        │
│         /    \                                               │
│       GPU3  GPU4                                             │
│                                                              │
│     Pros: O(log N) latency for small messages                │
│     优点：小消息时 O(log N) 延迟                              │
│     Cons: not bandwidth-optimal                              │
│     缺点：非带宽最优                                          │
│                                                              │
│  3. NVLS (NVLink SHARP — NVSwitch only)                      │
│     NVLS（NVLink SHARP — 仅限 NVSwitch）                     │
│                                                              │
│     GPU0 ─┐                                                  │
│     GPU1 ─┤                                                  │
│     GPU2 ─┼── NVSwitch performs reduction IN HARDWARE        │
│     GPU3 ─┤   NVSwitch 在硬件中执行归约                       │
│     GPU4 ─┤                                                  │
│     GPU5 ─┤   All GPUs send to switch simultaneously         │
│     GPU6 ─┤   所有 GPU 同时发送到交换机                       │
│     GPU7 ─┘   Switch returns reduced result                  │
│               交换机返回归约后的结果                           │
│                                                              │
│     Pros: O(1) latency! All GPUs in parallel!                │
│     优点：O(1) 延迟！所有 GPU 并行！                          │
│     Cons: requires NVSwitch (DGX systems only)               │
│     缺点：需要 NVSwitch（仅限 DGX 系统）                      │
│                                                              │
│  NCCL automatically selects the best algorithm               │
│  NCCL 自动选择最佳算法                                        │
│  based on message size, topology, and hardware               │
│  基于消息大小、拓扑和硬件                                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.6 NCCL + RDMA Data Flow (Multi-Node)

```
GPU on Node A wants to send gradient tensor to GPU on Node B:
节点 A 上的 GPU 想要向节点 B 上的 GPU 发送梯度张量：

Node A:
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  [GPU 0 VRAM]                                           │
│  ┌──────────────────────────────────────┐               │
│  │ Gradient Tensor                      │               │
│  │ (e.g., 256 MB in FP16)              │               │
│  └──────────────┬───────────────────────┘               │
│                 │                                        │
│                 │ NVLink / PCIe DMA                      │
│                 ▼                                        │
│  [System RAM — Pinned/CUDA Host Memory]                 │
│  ┌──────────────────────────────────────┐               │
│  │ Gradient copy (pinned buffer)        │               │
│  │ Registered with ibv_reg_mr()         │               │
│  │ r_key: 0xABCD                        │               │
│  └──────────────┬───────────────────────┘               │
│                 │                                        │
│                 │ RDMA NIC DMA-reads pinned memory       │
│                 │ RNIC DMA 读取固定内存                   │
│                 ▼                                        │
│  [Mellanox ConnectX-7 HCA]                              │
│  ┌──────────────────────────────────────┐               │
│  │ RDMA NIC constructs packet:          │               │
│  │ RDMA 网卡构造数据包：                  │               │
│  │                                      │               │
│  │ [Eth][IP][UDP][BTH][Data][ICRC]      │  ← RoCE v2   │
│  │ or                                    │               │
│  │ [LRH][BTH][Data][ICRC]               │  ← InfiniBand│
│  │                                      │               │
│  │ Hardware computes CRC, segments MTU   │               │
│  │ 硬件计算 CRC，分段 MTU                │               │
│  └──────────────┬───────────────────────┘               │
│                 │                                        │
│                 │ Wire: 400 Gbps (NDR IB)                │
│                 │ or 100 Gbps (RoCE v2)                  │
│                 ▼                                        │
└─────────────────────────────────────────────────────────┘
                  │
                  │ Physical cable (optical fiber)
                  │ 物理线缆（光纤）
                  ▼
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  [Mellanox ConnectX-7 HCA] on Node B                    │
│  ┌──────────────────────────────────────┐               │
│  │ NIC validates ICRC                    │               │
│  │ 网卡验证 ICRC                          │               │
│  │ NIC matches QP number                 │               │
│  │ 网卡匹配 QP 编号                       │               │
│  │ NIC looks up r_key (0xABCD)           │               │
│  │ 网卡查找 r_key                         │               │
│  │ NIC DMA-writes data directly into     │               │
│  │ registered user-space buffer           │               │
│  │ 网卡将数据直接 DMA 写入                 │               │
│  │ 已注册的用户空间缓冲区                  │               │
│  └──────────────┬───────────────────────┘               │
│                 │                                        │
│                 │ NO CPU INTERRUPT on Node B!             │
│                 │ 节点 B 无 CPU 中断！                    │
│                 ▼                                        │
│  [System RAM — Pinned/CUDA Host Memory]                 │
│  ┌──────────────────────────────────────┐               │
│  │ Gradient received (zero-copy)        │               │
│  │ 梯度已接收（零拷贝）                    │               │
│  └──────────────┬───────────────────────┘               │
│                 │                                        │
│                 │ NVLink / PCIe DMA                      │
│                 ▼                                        │
│  [GPU 1 VRAM]                                           │
│  ┌──────────────────────────────────────┐               │
│  │ Gradient Tensor (ready for reduce)   │               │
│  │ 梯度张量（准备进行归约）               │               │
│  └──────────────────────────────────────┘               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.7 NCCL Key Environment Variables

```bash
# === Network Selection ===
# === 网络选择 ===
NCCL_IB_DISABLE=0                  # Enable InfiniBand / 启用 InfiniBand
NCCL_SOCKET_IFNAME=eth0           # Network interface for bootstrap
                                   # 引导用网络接口
NCCL_IB_HCA=mlx5_0,mlx5_1        # Which IB HCAs to use
                                   # 使用哪些 IB HCA

# === Transport Tuning ===
# === 传输调优 ===
NCCL_P2P_DISABLE=0                 # Enable GPU P2P (NVLink/PCIe)
                                   # 启用 GPU P2P
NCCL_SHM_DISABLE=0                 # Enable shared memory transport
                                   # 启用共享内存传输
NCCL_NET_GDR_LEVEL=5              # GPU Direct RDMA level
                                   # GPU Direct RDMA 级别
NCCL_NET_GDR_READ=1               # Enable GDR read (NIC→GPU direct)
                                   # 启用 GDR 读取（NIC→GPU 直接）

# === Algorithm Selection ===
# === 算法选择 ===
NCCL_ALGO=Ring,Tree,NVLS          # Algorithms to use
                                   # 要使用的算法
NCCL_PROTO=Simple,LL,LL128        # Protocols (latency vs bandwidth)
                                   # 协议（延迟 vs 带宽）

# === Performance Tuning ===
# === 性能调优 ===
NCCL_BUFFSIZE=8388608              # Buffer size (8 MB default)
                                   # 缓冲区大小（默认 8 MB）
NCCL_MAX_NCHANNELS=16              # Max channels per connection
                                   # 每个连接的最大通道数
NCCL_MIN_NCHANNELS=4               # Min channels
                                   # 最小通道数
NCCL_NSOCKS_PERTHREAD=4            # Sockets per thread (NET transport)
                                   # 每线程套接字数（NET 传输）

# === Debugging ===
# === 调试 ===
NCCL_DEBUG=INFO                    # Debug level: VERSION/WARN/INFO/TRACE
                                   # 调试级别
NCCL_DEBUG_SUBSYS=INIT,NET,TUNING # Debug subsystem
                                   # 调试子系统
```

### 4.8 NCCL Performance Benchmarks (Real-World)

```
All-Reduce performance across typical configurations:
典型配置下的 All-Reduce 性能：

┌──────────────────────────────────────┬──────────────┬────────────┐
│ Configuration                        │ Message Size │ BusBW      │
│ 配置                                 │ 消息大小     │ 总线带宽    │
├──────────────────────────────────────┼──────────────┼────────────┤
│ 8× H100 NVLink (single DGX)         │ 1 GB         │ ~860 GB/s  │
│ 8× H100 NVLink（单 DGX）             │ 1 GB         │            │
├──────────────────────────────────────┼──────────────┼────────────┤
│ 8× H100 NVSwitch (NVLS algo)        │ 1 GB         │ ~900 GB/s  │
│ 8× H100 NVSwitch（NVLS 算法）        │ 1 GB         │            │
├──────────────────────────────────────┼──────────────┼────────────┤
│ 2× DGX H100 (16 GPU, 8× NDR IB)    │ 1 GB         │ ~450 GB/s  │
│ 2× DGX H100（16 GPU，8× NDR IB）     │ 1 GB         │ per node   │
│                                      │              │ 每节点      │
├──────────────────────────────────────┼──────────────┼────────────┤
│ 64× H100 (8 nodes × NDR IB)        │ 1 GB         │ ~420 GB/s  │
│ 64× H100（8 节点 × NDR IB）          │ 1 GB         │ per node   │
│                                      │              │ 每节点      │
├──────────────────────────────────────┼──────────────┼────────────┤
│ 8× A100 PCIe (single node)          │ 1 GB         │ ~250 GB/s  │
│ 8× A100 PCIe（单节点）               │ 1 GB         │            │
└──────────────────────────────────────┴──────────────┴────────────┘

BusBW = "bus bandwidth" = actual algorithm bandwidth 
        = 2 × (N-1)/N × per-GPU transfer rate
BusBW = "总线带宽" = 实际算法带宽 = 2 × (N-1)/N × 每 GPU 传输速率
```

---

## Summary — How They All Connect

# 总结 — 它们如何相互关联

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Application: PyTorch Distributed Training                   │
│  应用：PyTorch 分布式训练                                      │
│         │                                                    │
│         ▼                                                    │
│  NCCL (collective operations library)                        │
│  NCCL（集合操作库）                                            │
│         │                                                    │
│         ├─── intra-node ──▶ NVLink/PCIe (P2P transport)     │
│         │    节点内           NVLink/PCIe（P2P 传输）          │
│         │                                                    │
│         └─── inter-node ──▶ RDMA transport                   │
│              节点间            RDMA 传输                       │
│                     │                                        │
│                     ├── InfiniBand HCA                       │
│                     │   (native RDMA, lowest latency)        │
│                     │   （原生 RDMA，最低延迟）                │
│                     │                                        │
│                     └── RoCE v2 over Ethernet NIC            │
│                         (RDMA encapsulated in UDP/IP)        │
│                         （RDMA 封装在 UDP/IP 中）              │
│                             │                                │
│                             ▼                                │
│                     PFC + ECN (lossless Ethernet)            │
│                     PFC + ECN（无损以太网）                    │
│                                                              │
│  RDMA enables: zero-copy, kernel-bypass, CPU-free transfers  │
│  RDMA 实现：零拷贝、内核旁路、无 CPU 参与的数据传输            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

The combination of **RDMA** (zero-copy memory access), **NCCL** (optimal collective algorithms), **InfiniBand/RoCE v2** (high-bandwidth transport), and **PFC/ECN** (lossless delivery) together enable the massive multi-GPU, multi-node AI training and inference clusters that power today's largest language models.

**RDMA**（零拷贝内存访问）、**NCCL**（最优集合算法）、**InfiniBand/RoCE v2**（高带宽传输）和 **PFC/ECN**（无损传递）的组合，共同支撑了当今最大语言模型所需的大规模多 GPU、多节点 AI 训练和推理集群。
