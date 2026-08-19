---
title: NCCL 初始化（Init）全过程底层细节
date: 2026-09-07 22:30:00
tags:
  - NCCL
  - GPU
  - 分布式训练
  - PyTorch
categories:
  - GPU
---

## 零、从 Python 到 C 的调用链

在深入 NCCL Init 之前，先理清从用户代码到 NCCL 底层的完整调用路径：

```
用户 Python 代码:
  torch.distributed.init_process_group(backend='nccl', init_method='env://')
       │
       ▼
PyTorch C++ (torch/lib/libtorch_python.so):
  THDProcessGroupInit() → c10d::ProcessGroupNCCL::initProcessGroup()
       │
       ▼
PyTorch C++ (torch/lib/libtorch_cuda.so):
  c10d::ProcessGroupNCCL::initNCCLComm()
       │
       ▼
libnccl.so (NCCL 库):
  ncclCommInitAll()
       │
       ▼
  ncclCommInitRank()
       │
       ▼
  ncclCommInitRankFunc()    ← 这是核心函数，下面详细展开
       │
       ├── ncclTransportInit()
       ├── ncclTopoGetSystem()
       ├── ncclTopoCompute()
       ├── ncclTransportP2pConnect()
       ├── ncclTransportCollNetConnect()
       └── ncclCommInitRankSync()
```

---

## 一、Rendezvous 阶段

### 1.1 init_method='env://' 的含义

```python
# 用户代码
torch.distributed.init_process_group(
    backend='nccl',
    init_method='env://',       # ← 使用环境变量
    world_size=16,
    rank=5,
)
```

`env://` 表示不需要 URL-based rendezvous，而是从环境变量中读取所有信息：

```cpp
// torch/csrc/distributed/c10d/init.cpp (PyTorch 源码)

// 当 init_method == "env://" 时:
// 1. 从环境变量读取 MASTER_ADDR 和 MASTER_PORT
// 2. 创建 TCPStore（rank 0 创建 Server，其他 rank 创建 Client）
// 3. 使用 TCPStore 完成 rendezvous

std::string masterAddr = getEnvVar("MASTER_ADDR");  // "pytorchjob-mnist-master-0"
std::string masterPort = getEnvVar("MASTER_PORT");  // "23456"

// rank 0: 创建 TCPStore 的 Server 端
// rank > 0: 创建 TCPStore 的 Client 端，连接到 masterAddr:masterPort
auto store = std::make_shared<TCPStore>(
    masterAddr,
    std::stoi(masterPort),
    worldSize,
    isRank0,
    std::chrono::seconds(300),  // timeout
    /* waitWorkers */ true
);
```

### 1.2 TCPStore 的底层实现

```
                        TCPStore 架构
┌──────────────────────────────────────────────────────┐
│                   Rank 0 (Master)                      │
│                                                        │
│  TCPStoreServer (监听 23456 端口)                       │
│  ├── 主 acceptor loop                                  │
│  ├── 客户端连接管理                                      │
│  └── key-value 存储 (std::unordered_map)               │
│       key: "nccl/world_size"  → "16"                   │
│       key: "nccl/comm_id/0"   → "<binary>"             │
│       key: "torchelastic/num_ranks_registered" → "16"  │
└───────────────┬────────────────────────────────────────┘
                │ TCP 连接
     ┌──────────┼──────────┐
     │          │          │
     ▼          ▼          ▼
  Rank 1     Rank 2    ... Rank 15
  TCPStore   TCPStore      TCPStore
  Client     Client        Client
  (连接到      (连接到        (连接到
  23456)      23456)        23456)
```

TCPStore Server 的核心事件循环：

```cpp
// c10d/Store.cpp (简化)

void TCPStore::waitForWorkers() {
    // Rank 0 等待所有其他 rank 连接
    // 通过 key "torchelastic/num_ranks_registered" 判断
    
    // 每个 rank 连接后发送:
    //   SET "rank_<N>_ready" = "1"
    // Rank 0 轮询检查:
    //   if count("rank_*_ready") == worldSize - 1:
    //       break;  // 所有 rank 就绪
}
```

### 1.3 NCCL 内部的 Unique ID 交换

```
NCCL Init 之前，PyTorch ProcessGroupNCCL 需要交换 NCCL Unique ID:

// c10d/ProcessGroupNCCL.cpp

ProcessGroupNCCL::initNCCLComm(...) {
    // 1. Rank 0 生成 ncclUniqueId
    ncclUniqueId ncclId;
    if (rank_ == 0) {
        ncclGetUniqueId(&ncclId);  // 生成 128 字节的唯一标识
    }
    
    // 2. 通过 TCPStore 广播 ncclId 给所有 rank
    if (rank_ == 0) {
        store_->set("nccl_id_" + std::to_string(seqNum), 
                     serialize(ncclId));
    } else {
        auto data = store_->get("nccl_id_" + std::to_string(seqNum));
        ncclId = deserialize(data);
    }
    
    // 3. 所有 rank 使用同一个 ncclId 初始化 NCCL Communicator
    ncclCommInitRank(&comm, worldSize, ncclId, rank);
}
```

**ncclUniqueId 的结构：**

```c
// nccl.h
#define NCCL_UNIQUE_ID_BYTES 128

typedef struct {
    char internal[NCCL_UNIQUE_ID_BYTES];
} ncclUniqueId;

// internal 的实际内容:
// - 8 字节 magic number
// - 16 字节 IPv6 地址 (Rank 0 的地址)
// - 2 字节端口号
// - 8 字节进程 PID
// - 8 字节时间戳
// - 其余为随机字节
```

### 1.4 Rendezvous 的时序图

```
时间 →

Rank 0:                    Rank 1:                   Rank 2:
  │                          │                         │
  ├─ ncclGetUniqueId()       │                         │
  │  生成 ncclId             │                         │
  │                          │                         │
  ├─ TCPStore::set("nccl_id")│                         │
  │  存入 KV Store           │                         │
  │                          │                         │
  ├─ ncclCommInitRank()      ├─ TCPStore::get("nccl_id")│
  │  │                       │  取出 ncclId              │
  │  │                       │                           ├─ TCPStore::get("nccl_id")
  │  │                       ├─ ncclCommInitRank()        │  取出 ncclId
  │  │                       │  │                        │
  │  ▼                       │  ▼                        ├─ ncclCommInitRank()
  │  (进入 NCCL 内部初始化)    │  (进入 NCCL 内部初始化)     │  │
  │                          │                           │  ▼
  │                          │                           │  (进入 NCCL 内部初始化)
  │                          │                           │
  ├──NCCL 内部 Bootstrap 通信开始（所有 rank 互相连接）──────────┤
```

---

## 二、ncclCommInitRank 内部深入

### 2.1 顶层函数调用

```c
// src/init.cc (NCCL 源码)

ncclResult_t ncclCommInitRank(
    ncclComm_t* newcomm,
    int nranks,
    ncclUniqueId commId,
    int myrank
) {
    // 参数校验
    if (nranks < 1 || myrank < 0 || myrank >= nranks) {
        return ncclInvalidArgument;
    }
    
    // 分配 communicator 结构体
    struct ncclComm* comm;
    NCCLCHECK(ncclCalloc(&comm, 1));
    
    comm->rank = myrank;
    comm->nRanks = nranks;
    comm->commId = commId;
    
    // 初始化互斥锁
    pthread_mutex_init(&comm->lock, NULL);
    
    // 进入核心初始化函数
    NCCLCHECK(ncclCommInitRankFunc(comm));
    
    *newcomm = comm;
    return ncclSuccess;
}
```

### 2.2 ncclCommInitRankFunc 的完整流程

```c
// src/init.cc

static ncclResult_t ncclCommInitRankFunc(struct ncclComm* comm) {
    // ═══════════════════════════════════════════════
    // 阶段 1: Bootstrap 通信建立
    // ═══════════════════════════════════════════════
    
    // 1a. 通过 commId 建立 bootstrap 连接
    NCCLCHECK(ncclTransportInit(comm));
    // 内部使用 TCP/Socket 连接所有 rank
    
    // ═══════════════════════════════════════════════
    // 阶段 2: 拓扑发现
    // ═══════════════════════════════════════════════
    
    // 2a. 收集本节点的硬件拓扑信息
    struct ncclTopoSystem* system;
    NCCLCHECK(ncclTopoGetSystem(comm, &system));
    
    // ═══════════════════════════════════════════════
    // 阶段 3: 拓扑计算与路径选择
    // ═══════════════════════════════════════════════
    
    // 3a. 计算最优通信路径
    NCCLCHECK(ncclTopoCompute(comm, system));
    
    // ═══════════════════════════════════════════════
    // 阶段 4: 通信通道建立
    // ═══════════════════════════════════════════════
    
    // 4a. 建立 P2P / SHM / NET 连接
    NCCLCHECK(ncclTransportP2pConnect(comm, ...));
    
    // 4b. 如果有 CollNet，建立 CollNet 连接
    NCCLCHECK(ncclTransportCollNetConnect(comm, ...));
    
    // ═══════════════════════════════════════════════
    // 阶段 5: 同步验证
    // ═══════════════════════════════════════════════
    
    NCCLCHECK(ncclCommInitRankSync(comm));
    
    return ncclSuccess;
}
```

---

## 三、Bootstrap 通信建立（ncclTransportInit）

### 3.1 Bootstrap 连接的架构

NCCL 需要在初始化阶段建立一条 **控制通道（Bootstrap Channel）**，用于后续交换通信拓扑信息。这条通道独立于数据传输通道。

```
Bootstrap 网络拓扑:

  Rank 0 ──── TCP ──── Rank 1
    │                    │
    │                    │
  TCP                  TCP
    │                    │
    │                    │
  Rank 2 ──── TCP ──── Rank 3

特点:
  - 使用 TCP Socket（不是 IB/RDMA）
  - 仅用于初始化阶段的元数据交换
  - 初始化完成后可以关闭（或保留用于 reconnection）
  - 全连接拓扑：每个 rank 都知道所有其他 rank 的 bootstrap 地址
```

### 3.2 Bootstrap 连接建立代码

```c
// src/transport/net.cc

ncclResult_t ncclTransportInit(struct ncclComm* comm) {
    // 1. 解析 commId 得到 Rank 0 的 bootstrap 地址
    struct ncclSocketHandle listenAddr;
    NCCLCHECK(ncclSocketGetAddrFromUniqueId(comm->commId, &listenAddr));
    
    // 2. 创建本地监听 socket
    int listenFd;
    NCCLCHECK(ncclSocketCreate(&listenFd));
    NCCLCHECK(ncclSocketBind(listenFd, &localAddr));
    NCCLCHECK(ncclSocketListen(listenFd));
    
    // 3. 所有非 Rank 0 的进程连接到 Rank 0
    //    Rank 0 接受所有连接，收集所有 rank 的 bootstrap 地址
    if (comm->rank == 0) {
        // 接受 nRanks-1 个连接
        for (int i = 1; i < comm->nRanks; i++) {
            int peerFd;
            NCCLCHECK(ncclSocketAccept(listenFd, &peerFd));
            
            // 读取对方的 bootstrap 地址
            struct ncclSocketHandle peerAddr;
            NCCLCHECK(ncclSocketRecv(peerFd, &peerAddr, sizeof(peerAddr)));
            
            // 存储到全局地址表
            comm->bootstrapAddrs[i] = peerAddr;
        }
        
        // 4. Rank 0 将完整的地址表广播给所有 rank
        for (int i = 1; i < comm->nRanks; i++) {
            NCCLCHECK(ncclSocketSend(comm->bootstrapFds[i], 
                                     comm->bootstrapAddrs, 
                                     sizeof(struct ncclSocketHandle) * comm->nRanks));
        }
    } else {
        // 连接到 Rank 0
        int rank0Fd;
        NCCLCHECK(ncclSocketConnect(&listenAddr, &rank0Fd));
        
        // 发送自己的 bootstrap 地址
        NCCLCHECK(ncclSocketSend(rank0Fd, &localAddr, sizeof(localAddr)));
        
        // 接收完整的地址表
        NCCLCHECK(ncclSocketRecv(rank0Fd, 
                                 comm->bootstrapAddrs, 
                                 sizeof(struct ncclSocketHandle) * comm->nRanks));
    }
    
    // 5. 所有 rank 互相建立 TCP 连接（全连接）
    for (int i = 0; i < comm->nRanks; i++) {
        if (i == comm->rank) continue;
        
        if (comm->rank < i) {
            // 较小 rank 先监听，较大 rank 来连接
            NCCLCHECK(ncclSocketAccept(listenFd, &comm->bootstrapFds[i]));
        } else {
            NCCLCHECK(ncclSocketConnect(&comm->bootstrapAddrs[i], &comm->bootstrapFds[i]));
        }
    }
    
    return ncclSuccess;
}
```

### 3.3 Bootstrap 消息交换协议

Bootstrap 建立后，所有 rank 通过它交换拓扑信息：

```
Bootstrap 消息格式:

struct ncclBootstrapMessage {
    uint32_t magic;          // 0x4E43434C ("NCCL")
    uint32_t version;        // NCCL 协议版本
    uint32_t rank;
    uint32_t nRanks;
    
    // 拓扑信息
    struct {
        int cudaDev;             // CUDA device index
        int gdrSupport;          // GPUDirect RDMA 支持
        int netDev;              // 网络设备 ID
        char busId[16];          // PCI Bus ID (如 "0000:3b:00.0")
        int numaNode;            // NUMA node ID
        
        // 传输能力
        struct {
            int p2p;             // P2P 支持 (NVLink/PCIe)
            int shm;             // 共享内存支持
            int collnet;         // CollNet 支持
        } transports;
    } local;
    
    // 对端连接信息
    struct {
        int nDevs;
        struct ncclNetDevice dev[NCCL_NET_MAX_DEVS];
    } net;
};

// 交换流程:
// Round 1: 所有 rank → 所有其他 rank, 发送自己的 local 信息
// Round 2: 所有 rank 收集完所有其他 rank 的信息
// Round 3: 进入拓扑计算
```

---

## 四、拓扑发现（ncclTopoGetSystem）

### 4.1 系统拓扑的采集

NCCL 通过读取 `sysfs` 和 `PCI` 配置空间来发现完整的硬件拓扑：

```c
// src/graph/topo.cc

ncclResult_t ncclTopoGetSystem(struct ncclComm* comm, struct ncclTopoSystem** system) {
    struct ncclTopoSystem* sys;
    NCCLCHECK(ncclCalloc(&sys, 1));
    
    // ══════════════════════════════════════
    // Step 1: 扫描所有 PCI 设备
    // ══════════════════════════════════════
    
    // 读取 /sys/bus/pci/devices/
    DIR* dir = opendir("/sys/bus/pci/devices");
    struct dirent* entry;
    while ((entry = readdir(dir)) != NULL) {
        // 对每个 PCI 设备读取:
        //   /sys/bus/pci/devices/<BDF>/vendor
        //   /sys/bus/pci/devices/<BDF>/device
        //   /sys/bus/pci/devices/<BDF>/class
        //   /sys/bus/pci/devices/<BDF>/subsystem_vendor
        //   /sys/bus/pci/devices/<BDF>/numa_node
        //   /sys/bus/pci/devices/<BDF>/resource         (BAR 地址)
        //   /sys/bus/pci/devices/<BDF>/current_link_speed
        //   /sys/bus/pci/devices/<BDF>/current_link_width
        
        struct ncclTopoNode node;
        node.busId = parseBDF(entry->d_name);
        node.device = readIntFile(entry->d_name, "/device");
        node.vendor = readIntFile(entry->d_name, "/vendor");
        node.numaNode = readIntFile(entry->d_name, "/numa_node");
        
        // 识别设备类型
        if (node.vendor == 0x10de && isGPU(node.device)) {
            node.type = GPU;
        } else if (node.vendor == 0x15b3) {  // Mellanox
            node.type = NET;
        } else if (node.vendor == 0x8086) {  // Intel
            node.type = (isNVSwitch(node)) ? NVS : PCI;
        }
        
        ncclTopoAddNode(sys, &node);
    }
    
    // ══════════════════════════════════════
    // Step 2: 构建 PCI 拓扑树
    // ══════════════════════════════════════
    
    // 读取 PCI bridge 和 switch 的拓扑关系
    // /sys/bus/pci/devices/<BDF>/ 之间的 parent 关系
    // 构建出:
    //
    //  CPU Socket 0
    //    ├── PCIe Root Complex
    //    │     ├── PCIe Switch (downstream)
    //    │     │     ├── GPU 0 (3b:00.0)
    //    │     │     └── GPU 1 (3e:00.0)
    //    │     └── PCIe Switch (downstream)
    //    │           ├── GPU 2 (60:00.0)
    //    │           └── GPU 3 (63:00.0)
    //    ├── NVLink
    //    │     ├── GPU 0 ←NVLink→ GPU 1
    //    │     ├── GPU 1 ←NVLink→ GPU 2
    //    │     └── GPU 2 ←NVLink→ GPU 3
    //    └── InfiniBand HCA (mlx5_0)
    //
    //  CPU Socket 1
    //    ├── PCIe Root Complex
    //    │     └── ... (GPU 4~7)
    //    └── InfiniBand HCA (mlx5_1)
    
    // ══════════════════════════════════════
    // Step 3: 检测 P2P 连接 (NVLink/NVSwitch)
    // ══════════════════════════════════════
    
    // 方法 1: 读取 NVML
    nvmlInit();
    nvmlDevice_t dev;
    nvmlDeviceGetHandleByIndex(gpuIndex, &dev);
    
    nvmlP2PStatus_t p2pStatus;
    nvmlDeviceGetP2PStatus(dev, peerDev, NVML_P2P_CAPABILITY_INDEX_NVLINK, &p2pStatus);
    
    // 方法 2: 读取 sysfs NVLink 信息
    // /sys/bus/pci/devices/<GPU_BDF>/nvlink/<link_id>/status
    // /sys/bus/pci/devices/<GPU_BDF>/nvlink/<link_id>/bandwidth
    
    for (int link = 0; link < 18; link++) {  // A100 最多 12 条 NVLink
        char path[256];
        sprintf(path, "/sys/bus/pci/devices/%s/nvlink/%d/status", busId, link);
        
        int status = readIntFile(path);
        if (status & NVLINK_STATUS_ACTIVE) {
            // 活跃的 NVLink 连接
            int peerGpu = getNVLinkPeerGpu(busId, link);
            int bandwidth = getNVLinkBandwidth(busId, link);  // 如 25 GB/s per link
            
            sys->nvlinks[nNvlinks++] = {srcGpu, peerGpu, link, bandwidth};
        }
    }
    
    *system = sys;
    return ncclSuccess;
}
```

### 4.2 拓扑数据结构

```c
// src/include/nccl.h (NCCL 内部头文件, 简化表示)

struct ncclTopoNode {
    int type;            // GPU / NET / PCI / CPU / NVS (NVSwitch) / NIC
    int busId;           // PCI BDF
    int numaNode;
    int gpu;             // GPU index
    int net;             // 网络设备 index
    
    // 连接到的其他节点
    int nLinks;
    struct ncclTopoLink {
        int type;        // P2P (NVLink) / SYS (PCIe) / NET (IB) / NAV (不可达)
        int bandwidth;   // GB/s
        int latency;     // ns
        struct ncclTopoNode* remNode;
    } links[NCCL_TOPO_MAX_LINKS];
};

struct ncclTopoSystem {
    int nNodes;
    struct ncclTopoNode nodes[NCCL_TOPO_MAX_NODES];
    
    // 每个节点的路径信息（最短路径）
    int paths[NCCL_TOPO_MAX_NODES][NCCL_TOPO_MAX_NODES];
    
    // NVLink 矩阵
    int nvlinkMatrix[NCCL_MAX_LOCAL_RANKS][NCCL_MAX_LOCAL_RANKS];
    // nvlinkMatrix[i][j] = GPU_i 到 GPU_j 的 NVLink 带宽 (GB/s)
    // 如:
    //       GPU0  GPU1  GPU2  GPU3  GPU4  GPU5  GPU6  GPU7
    // GPU0  [  0,   50,   25,   25,    0,    0,    0,    0]
    // GPU1  [ 50,    0,   25,   25,    0,    0,    0,    0]
    // GPU2  [ 25,   25,    0,   50,    0,    0,    0,    0]
    // ...
};
```

### 4.3 NVLink 拓扑的实际数据示例（8×A100 节点）

```
A100 SXM4 NVLink 拓扑 (8 GPU):

NVLink 连接矩阵 (GB/s):
         GPU0  GPU1  GPU2  GPU3  GPU4  GPU5  GPU6  GPU7
GPU0  [    0,   600,  300,  300,    0,    0,    0,    0]  ← 通过 NVSwitch
GPU1  [  600,    0,  300,  300,    0,    0,    0,    0]
GPU2  [  300,  300,    0,  600,    0,    0,    0,    0]
GPU3  [  300,  300,  600,    0,    0,    0,    0,    0]
GPU4  [    0,    0,    0,    0,    0,  600,  300,  300]
GPU5  [    0,    0,    0,    0,  600,    0,  300,  300]
GPU6  [    0,    0,    0,    0,  300,  300,    0,  600]
GPU7  [    0,    0,    0,    0,  300,  300,  600,    0]

NVSwitch 布局:
  NVSwitch 0: 连接 GPU0~GPU3 (Socket 0 上)
  NVSwitch 1: 连接 GPU4~GPU7 (Socket 1 上)

  GPU0 ←NVLink(12×25GB/s=300GB/s)→ NVSwitch0 ←NVLink(12×25GB/s=300GB/s)→ GPU2
  跨 NVSwitch: GPU0 → NVSwitch0 → NVSwitch1 → GPU4 = 300GB/s (受限于 bridge)

IB 连接:
  mlx5_0 (IB HCA) ←PCIe Gen4 x16→ Socket 0 (GPU0~GPU3 共享)
  mlx5_1 (IB HCA) ←PCIe Gen4 x16→ Socket 1 (GPU4~GPU7 共享)
```

---

## 五、拓扑计算与通信通道构建（ncclTopoCompute）

### 5.1 搜索算法

NCCL 使用 **贪心搜索 + 图遍历** 来决定每个通信操作使用哪些路径：

```c
// src/graph/topo.cc (简化)

ncclResult_t ncclTopoCompute(struct ncclComm* comm, struct ncclTopoSystem* system) {
    
    // 目标：为 AllReduce / AllGather / ReduceScatter 等集合操作
    // 找到最优的通信通道（channels）
    // 每个 channel 包含一条 ring 或 tree 的路径
    
    // ─────────────────────────────────────
    // Phase 1: 确定 Search 方式
    // ─────────────────────────────────────
    
    // 读取环境变量 NCCL_TOPO_FILE 或自动检测
    int searchType;
    if (getenv("NCCL_TOPO_FILE")) {
        searchType = TOPO_FILE;        // 用户自定义拓扑文件
    } else if (system->nNodes <= 8) {
        searchType = TOPO_EXPL;        // 穷举搜索（小规模）
    } else {
        searchType = TOPO_BINARY;      // 二分搜索（大规模）
    }
    
    // ─────────────────────────────────────
    // Phase 2: 构建 Ring 通道
    // ─────────────────────────────────────
    
    // 搜索最优的 Ring 拓扑
    // 约束：每个 rank 的入边和出边必须使用不同的传输方式
    //       （不能两条边都走 NVLink，因为 PCIe NIC 限制）
    
    int nChannels = 0;
    struct ncclTopoGraph graphs[NCCL_MAX_CHANNELS];
    
    for (int c = 0; c < NCCL_MAX_CHANNELS; c++) {
        struct ncclTopoGraph* graph = &graphs[c];
        
        // 搜索算法
        switch (searchType) {
        case TOPO_EXPL:
            // 穷举所有可能的环路
            // 使用 DFS + 剪枝
            NCCLCHECK(ncclTopoSearchExplist(comm, system, graph));
            break;
            
        case TOPO_BINARY:
            // 二分法 + 贪心
            NCCLCHECK(ncclTopoSearchBinary(comm, system, graph));
            break;
        }
        
        if (graph->nHops == 0) break;  // 搜索失败
        nChannels++;
        
        // 标记已使用的路径，避免后续 channel 冲突
        NCCLCHECK(ncclTopoMarkUsed(graph, system));
    }
    
    comm->nChannels = nChannels;
    
    // ─────────────────────────────────────
    // Phase 3: 同时搜索 Tree 通道
    // ─────────────────────────────────────
    
    // Tree 用于 AllReduce 的 ReduceScatter 阶段
    // Ring 用于 AllReduce 的 AllGather 阶段
    
    for (int c = 0; c < comm->nChannels; c++) {
        struct ncclTopoGraph* tree = &comm->channels[c].tree;
        NCCLCHECK(ncclTopoSearchTree(comm, system, c, tree));
    }
    
    // ─────────────────────────────────────
    // Phase 4: 确定每条边使用的传输方式
    // ─────────────────────────────────────
    
    // 对 Ring 中的每条边 (src → dst)，决定使用哪种传输:
    //   P2P  (NVLink / NVSwitch) → 最高带宽
    //   SHM  (共享内存, /dev/shm) → 中等带宽，仅限同节点
    //   NET  (IB/RoCE)           → 跨节点，200~400 Gbps
    //   COLL (CollNet/SHARP)     → 网络内聚合
    
    for (int c = 0; c < comm->nChannels; c++) {
        struct ncclChannel* channel = &comm->channels[c];
        
        for (int i = 0; i < comm->nRanks; i++) {
            int nextRank = channel->ring.next;
            int prevRank = channel->ring.prev;
            
            // 判断 nextRank 的传输方式
            channel->ring.sendTransport = selectTransport(
                comm, comm->rank, nextRank, system);
            // 返回: TRANSPORT_P2P / TRANSPORT_SHM / TRANSPORT_NET / TRANSPORT_COLL
            
            channel->ring.recvTransport = selectTransport(
                comm, prevRank, comm->rank, system);
        }
    }
    
    return ncclSuccess;
}
```

### 5.2 传输方式的选择逻辑

```c
// src/transport/transport.cc

enum ncclTransportType selectTransport(
    struct ncclComm* comm,
    int srcRank, 
    int dstRank,
    struct ncclTopoSystem* system
) {
    int srcNode = system->nodes[srcRank].gpu;
    int dstNode = system->nodes[dstRank].gpu;
    int sameNode = (srcNode / GPUs_per_node == dstNode / GPUs_per_node);
    
    // 优先级: P2P > SHM > NET > COLL
    
    if (sameNode) {
        // 同节点
        if (canP2P(srcNode, dstNode)) {
            // NVLink 或 PCIe P2P 可用
            return TRANSPORT_P2P;
        }
        // fallback: 共享内存
        return TRANSPORT_SHM;
    } else {
        // 跨节点
        if (comm->localRanks == 0) {
            // 本节点负责网络通信
            return TRANSPORT_NET;
        }
        // 通过本节点 rank 0 代理网络通信
        // rank 0 通过 NET 发送到远端 rank 0
        // 远端 rank 0 通过 P2P 分发给本节点其他 rank
        return TRANSPORT_PROXY;
    }
}
```

### 5.3 Ring 拓扑的实际构建示例

```
4 节点 × 8 GPU = 32 ranks

NCCL 自动构建的 Ring (Channel 0):
  Ring: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 
        → 15 → 14 → 13 → 12 → 11 → 10 → 9 → 8
        → 16 → 17 → 18 → 19 → 20 → 21 → 22 → 23
        → 31 → 30 → 29 → 28 → 27 → 26 → 25 → 24
        → 0 (闭合)

每条边的传输方式:
  0→1:   P2P (NVLink, 600 GB/s)     同节点
  1→2:   P2P (NVLink, 600 GB/s)     同节点
  ...
  7→15:  NET (IB, 200 Gbps)         跨节点
  15→14: P2P (NVLink, 600 GB/s)     同节点
  ...
  23→31: NET (IB, 200 Gbps)         跨节点
  31→30: P2P (NVLink, 600 GB/s)     同节点
  ...
  24→0:  NET (IB, 200 Gbps)         跨节点
  0: 闭合

Tree 拓扑 (Channel 0):
  Root: rank 0
  ├── Children: rank 1, rank 8
  │   ├── rank 1 → Children: rank 2, rank 3
  │   └── rank 8 → Children: rank 9, rank 16
  │       ├── rank 9 → Children: rank 10, rank 11
  │       └── rank 16 → Children: rank 17, rank 24
  │           ...

  Tree 用于 Reduce-Scatter 阶段 (向上聚合)
  Ring 用于 All-Gather 阶段 (环形分发)
```

---

## 六、P2P 访问验证（cudaIpcOpenMemHandle）

### 6.1 CUDA P2P 访问的底层机制

```c
// NCCL 在建立通道前，需要验证 GPU 之间是否可以 P2P 访问

// src/transport/p2p.cc

ncclResult_t ncclTransportP2pSetup(struct ncclComm* comm, struct ncclTopoGraph* graph) {
    
    for (int c = 0; c < comm->nChannels; c++) {
        struct ncclChannel* channel = &comm->channels[c];
        int peer = channel->ring.next;
        
        // ─────────────────────────────────────
        // Step 1: 检查 P2P 能力
        // ─────────────────────────────────────
        
        int canAccessPeer = 0;
        CUDACHECK(cudaDeviceCanAccessPeer(&canAccessPeer, comm->cudaDev, peer));
        
        if (!canAccessPeer) {
            // 退化到 SHM 或 NET 传输
            return ncclInternalError;
        }
        
        // ─────────────────────────────────────
        // Step 2: 启用 P2P 访问
        // ─────────────────────────────────────
        
        CUDACHECK(cudaDeviceEnablePeerAccess(peer, 0));
        // 这会在本 GPU 的页表中添加对端 GPU 显存的映射
        
        // ─────────────────────────────────────
        // Step 3: 注册 IPC Handle
        // ─────────────────────────────────────
        
        // 分配本地 IPC buffer
        void* localIpcBuffer;
        CUDACHECK(cudaMalloc(&localIpcBuffer, IPC_BUFFER_SIZE));
        
        // 获取 IPC Handle (用于跨进程共享 GPU 内存)
        cudaIpcMemHandle_t ipcHandle;
        CUDACHECK(cudaIpcGetMemHandle(&ipcHandle, localIpcBuffer));
        
        // 通过 Bootstrap 通道将 IPC Handle 发送给对端
        NCCLCHECK(bootstrapSend(comm, peer, &ipcHandle, sizeof(ipcHandle)));
        
        // 接收对端的 IPC Handle
        cudaIpcMemHandle_t peerIpcHandle;
        NCCLCHECK(bootstrapRecv(comm, peer, &peerIpcHandle, sizeof(peerIpcHandle)));
        
        // 打开对端的 IPC Handle → 得到对端显存在本进程地址空间的映射
        void* peerIpcBuffer;
        CUDACHECK(cudaIpcOpenMemHandle(
            &peerIpcBuffer,
            peerIpcHandle,
            cudaIpcMemLazyEnablePeerAccess  // 延迟建立访问
        ));
        
        // ─────────────────────────────────────
        // Step 4: 分配 Ring Buffer
        // ─────────────────────────────────────
        
        // 每个 channel 需要两个 ring buffer:
        //   - Send Buffer: 存放即将发送的数据
        //   - Recv Buffer: 存放接收到的数据
        
        void* sendBuffer;
        void* recvBuffer;
        CUDACHECK(cudaMalloc(&sendBuffer, comm->buffSizes[c]));
        CUDACHECK(cudaMalloc(&recvBuffer, comm->buffSizes[c]));
        
        // 注册到 transport connection
        channel->ring.send.conn.buffs = sendBuffer;
        channel->ring.recv.conn.buffs = peerIpcBuffer;  // 指向对端的显存
        
        // ─────────────────────────────────────
        // Step 5: 分配 Signal/Fence 用于同步
        // ─────────────────────────────────────
        
        // NCCL 使用 CUDA IPC 信号量进行 GPU 间同步
        cudaIpcEventHandle_t localEventHandle, peerEventHandle;
        cudaEvent_t localEvent, peerEvent;
        
        CUDACHECK(cudaEventCreate(&localEvent, 
            cudaEventDisableTiming | cudaEventInterprocess));
        CUDACHECK(cudaIpcGetEventHandle(&localEventHandle, localEvent));
        
        // 交换 Event Handle
        NCCLCHECK(bootstrapSend(comm, peer, &localEventHandle, sizeof(localEventHandle)));
        NCCLCHECK(bootstrapRecv(comm, peer, &peerEventHandle, sizeof(peerEventHandle)));
        
        CUDACHECK(cudaIpcOpenEventHandle(&peerEvent, peerEventHandle));
        
        channel->ring.send.conn.opaqueComm = localEvent;
        channel->ring.recv.conn.opaqueComm = peerEvent;
    }
    
    return ncclSuccess;
}
```

### 6.2 cudaIpcOpenMemHandle 的底层工作原理

```
                    进程 A (Rank 0)              进程 B (Rank 1)
                    ┌──────────────┐            ┌──────────────┐
                    │   虚拟地址空间  │            │   虚拟地址空间  │
                    │              │            │              │
                    │  0x7f00...   │            │  0x7f00...   │
                    │  ┌────────┐ │            │  ┌────────┐ │
                    │  │ Local  │ │            │  │ Local  │ │
                    │  │ Buffer │ │            │  │ Buffer │ │
                    │  │ 16MB   │ │            │  │ 16MB   │ │
                    │  └────────┘ │            │  └────────┘ │
                    │              │            │              │
                    │  0x7f10...   │            │  0x7f10...   │
                    │  ┌────────┐ │  cudaIpc   │  ┌────────┐ │
                    │  │ Peer   │←├─OpenMem──→├─→│ Peer   │ │
                    │  │ Buffer │ │  Handle    │  │ Buffer │ │
                    │  │ (映射B) │ │            │  │ (映射A) │ │
                    │  └────────┘ │            │  └────────┘ │
                    └──────┬───────┘            └──────┬───────┘
                           │                           │
                    ┌──────┴───────┐            ┌──────┴───────┐
                    │   GPU 0      │            │   GPU 1      │
                    │   显存       │            │   显存        │
                    │  ┌────────┐ │            │  ┌────────┐ │
                    │  │实际数据 │←├───NVLink───├→│ 实际数据 │ │
                    │  │物理地址  │ │   /PCIe     │  │物理地址  │ │
                    │  └────────┘ │            │  └────────┘ │
                    └──────────────┘            └──────────────┘

关键点:
1. cudaIpcOpenMemHandle 不拷贝数据，而是建立GPU显存的地址映射
2. NVLink: 通过 NVLink 硬件直接读写对端 GPU 显存
3. PCIe P2P: 通过 PCIe Switch/Root Complex 转发
4. 两种方式的带宽差异巨大:
   - NVLink 3.0: 50 GB/s per link × 12 links = 600 GB/s (A100)
   - PCIe Gen4 x16: ~32 GB/s (单向)
```

### 6.3 P2P 访问验证失败的 fallback

```c
// 当 cudaDeviceCanAccessPeer 返回 false 时

// 可能的原因:
// 1. 不同 CPU Socket 上的 GPU，PCIe P2P 被 BIOS 禁用
// 2. GPU 驱动版本不匹配
// 3. IOMMU 阻止了 P2P 访问

// NCCL 的 fallback 策略:
if (!canP2P) {
    if (sameNode) {
        // 同节点: 使用 SHM (共享内存)
        // 通过 /dev/shm 或 mmap 建立进程间共享内存
        // 数据路径: GPU0 → CPU → /dev/shm → CPU → GPU1
        // 带宽: 受限于 PCIe + CPU 内存带宽
        transport = TRANSPORT_SHM;
    } else {
        // 跨节点: 使用 NET (IB/RoCE)
        // 正常路径，不退化
        transport = TRANSPORT_NET;
    }
}
```

---

## 七、IB Queue Pair (QP) 的建立

### 7.1 NCCL 网络层初始化

```c
// src/transport/net.cc

ncclResult_t ncclTransportNetSetup(struct ncclComm* comm) {
    
    // ─────────────────────────────────────
    // Step 1: 加载网络插件
    // ─────────────────────────────────────
    
    // NCCL 2.x+ 使用插件式网络层
    // 搜索顺序:
    //   1. NCCL_NET_PLUGIN 环境变量指定的 .so
    //   2. libnccl-net.so (通用网络插件)
    //   3. 内置 Socket 传输 (fallback)
    
    void* netPlugin = dlopen(getenv("NCCL_NET_PLUGIN") ?: "libnccl-net.so", RTLD_NOW);
    
    // 插件必须实现的接口:
    struct ncclNet {
        const char* name;                                              // "IB"
        ncclResult_t (*init)(ncclDebugLogger_t);                       // 初始化
        ncclResult_t (*devices)(int* ndev);                            // 返回设备数量
        ncclResult_t (*getProperties)(int dev, ncclNetProperties_t*);  // 设备属性
        ncclResult_t (*listen)(int dev, void** handle);                // 监听连接
        ncclResult_t (*connect)(int dev, void* handle, void** conn);   // 连接对端
        ncclResult_t (*accept)(void* listenComm, void** conn);         // 接受连接
        ncclResult_t (*regMr)(void* conn, void* data, int size, int type, void** mhandle);  // 注册 MR
        ncclResult_t (*isend)(void* conn, void* data, int size, void* mhandle, void** request); // 异步发送
        ncclResult_t (*irecv)(void* conn, void* n, void** data, int sizes[], void** mhandles, void** requests[]); // 异步接收
        ncclResult_t (*test)(void* request);                           // 检查完成
        ncclResult_t (*closeSend)(void* conn);
        ncclResult_t (*closeRecv)(void* conn);
        ncclResult_t (*closeListen)(void* listenComm);
    };
    
    // ─────────────────────────────────────
    // Step 2: IB 设备发现
    // ─────────────────────────────────────
    
    int nDevs;
    NCCLCHECK(ncclNet->devices(&nDevs));
    
    // IB 插件内部 (ibv_get_device_list):
    // struct ibv_device** devList = ibv_get_device_list(&numDevices);
    // 
    // 对于每个 IB 设备，读取:
    //   /sys/class/infiniband/mlx5_0/ports/1/state     → "ACTIVE"
    //   /sys/class/infiniband/mlx5_0/ports/1/rate      → "200 Gb/sec"
    //   /sys/class/infiniband/mlx5_0/ports/1/lid        → (Local ID)
    //   /sys/class/infiniband/mlx5_0/ports/1/gids/0     → (GID for RoCE)
    
    for (int d = 0; d < nDevs; d++) {
        ncclNetProperties_t props;
        ncclNet->getProperties(d, &props);
        
        // props.name = "mlx5_0"
        // props.pciPath = "0000:3b:00.0"
        // props.speed = 200000  (200 Gbps)
        // props.port = 1
        // props.maxComms = 65536
        // props.latency = 500  (500 ns)
    }
    
    return ncclSuccess;
}
```

### 7.2 Queue Pair (QP) 创建的详细过程

```c
// nccl-net-ib 插件内部 (nccl-net-ib/ibvwrap.cc 或类似)

ncclResult_t ibSetupConnection(struct ncclIbConnection* conn) {
    
    // ══════════════════════════════════════
    // Phase 1: 获取 IB 设备上下文
    // ══════════════════════════════════════
    
    struct ibv_context* ctx;
    ctx = ibv_open_device(ibDev);  // 打开 /dev/infiniband/verbs0
    
    // 查询设备能力
    struct ibv_device_attr devAttr;
    ibv_query_device(ctx, &devAttr);
    // devAttr.max_qp = 262144        (最大 QP 数量)
    // devAttr.max_qp_wr = 32768      (每个 QP 的最大 WR 数量)
    // devAttr.max_cq = 65536         (最大 CQ 数量)
    // devAttr.max_mr = 524288        (最大 MR 数量)
    
    // ══════════════════════════════════════
    // Phase 2: 创建 Protection Domain (PD)
    // ══════════════════════════════════════
    
    struct ibv_pd* pd;
    pd = ibv_alloc_pd(ctx);
    // PD 是内存注册和 QP 的权限域
    // 同一 PD 内的 QP 可以访问同一 PD 内注册的 MR
    
    // ══════════════════════════════════════
    // Phase 3: 创建 Completion Queue (CQ)
    // ══════════════════════════════════════
    
    struct ibv_cq* sendCq;
    struct ibv_cq* recvCq;
    sendCq = ibv_create_cq(ctx, CQ_DEPTH, NULL, NULL, 0);
    recvCq = ibv_create_cq(ctx, CQ_DEPTH, NULL, NULL, 0);
    // CQ_DEPTH 通常 = 4096 或 8192
    // 每个完成的 Work Request 在 CQ 中产生一个 CQE (Completion Queue Entry)
    
    // ══════════════════════════════════════
    // Phase 4: 创建 Queue Pair (QP)
    // ══════════════════════════════════════
    
    struct ibv_qp_init_attr qpInitAttr = {
        .send_cq = sendCq,
        .recv_cq = recvCq,
        .cap = {
            .max_send_wr = 4096,     // 发送队列深度
            .max_recv_wr = 4096,     // 接收队列深度
            .max_send_sge = 1,       // 每个 WR 的最大 scatter-gather 元素数
            .max_recv_sge = 1,
            .max_inline_data = 128,  // 内联数据的最大大小
        },
        .qp_type = IBV_QPT_RC,      // Reliable Connection (保证可靠传输)
    };
    
    struct ibv_qp* qp;
    qp = ibv_create_qp(pd, &qpInitAttr);
    // 创建 RC QP，此时 QP 处于 RESET 状态
    
    // ══════════════════════════════════════
    // Phase 5: QP 状态机转换
    // ══════════════════════════════════════
    
    // IB QP 有严格的状态机:
    // RESET → INIT → RTR (Ready to Receive) → RTS (Ready to Send)
    
    // Step 5a: RESET → INIT
    struct ibv_qp_attr attr;
    int attr_mask;
    
    memset(&attr, 0, sizeof(attr));
    attr.qp_state = IBV_QPS_INIT;
    attr.pkey_index = 0;                // Partition Key 索引
    attr.port_num = ibPort;              // IB 端口号 (通常 = 1)
    attr.qp_access_flags =              // 访问权限
        IBV_ACCESS_LOCAL_WRITE  |
        IBV_ACCESS_REMOTE_READ  |
        IBV_ACCESS_REMOTE_WRITE |
        IBV_ACCESS_REMOTE_ATOMIC;
    
    ibv_modify_qp(qp, &attr,
        IBV_QP_STATE      |
        IBV_QP_PKEY_INDEX  |
        IBV_QP_PORT        |
        IBV_QP_ACCESS_FLAGS);
    // QP 现在处于 INIT 状态，可以注册 MR 了
    
    // ══════════════════════════════════════
    // Phase 6: 注册 Memory Region (MR)
    // ══════════════════════════════════════
    
    // 关键: 使用 GPUDirect RDMA 时，注册的是 GPU 显存地址
    void* gpuBuffer;  // 由 NCCL 分配的 CUDA buffer
    cudaHostAlloc(&gpuBuffer, size, cudaHostAllocDefault);
    // 或者对于 GPUDirect RDMA:
    // gpuBuffer = cudaMalloc'ed 的 GPU 显存地址
    
    struct ibv_mr* mr;
    mr = ibv_reg_mr(pd, gpuBuffer, size,
        IBV_ACCESS_LOCAL_WRITE  |
        IBV_ACCESS_REMOTE_READ  |
        IBV_ACCESS_REMOTE_WRITE |
        IBV_ACCESS_REMOTE_ATOMIC);
    // mr->lkey: 本地访问的 Key
    // mr->rkey: 远端访问的 Key
    //
    // GPUDirect RDMA 的魔力:
    // ibv_reg_mr 会通过内核驱动 (mlx5_core + peer_mem) 
    // 将 GPU 显存页注册到 HCA 的 Page Table
    // HCA 之后可以直接通过 PCIe 读写 GPU 显存，无需 CPU 参与
    
    // 对端信息交换 (通过 Bootstrap 通道)
    struct ncclIbQpInfo {
        uint32_t qpNum;     // QP 编号 (由 HCA 分配)
        uint16_t lid;       // Local ID (IB 子网内唯一)
        uint8_t  gid[16];   // Global ID (用于跨子网/RoCE)
        uint32_t rkey;      // Remote Key (远端访问 MR 的权限)
        uint64_t addr;      // 远端 buffer 的虚拟地址
    };
    
    struct ncclIbQpInfo localInfo = {
        .qpNum = qp->qp_num,
        .lid   = getLocalId(ibPort),
        .gid   = getGid(ibPort, gidIndex),
        .rkey  = mr->rkey,
        .addr  = (uint64_t)gpuBuffer,
    };
    
    // 通过 Bootstrap 交换
    bootstrapSend(comm, peer, &localInfo, sizeof(localInfo));
    bootstrapRecv(comm, peer, &remoteInfo, sizeof(remoteInfo));
    
    // ══════════════════════════════════════
    // Phase 7: INIT → RTR (Ready to Receive)
    // ══════════════════════════════════════
    
    memset(&attr, 0, sizeof(attr));
    attr.qp_state = IBV_QPS_RTR;
    attr.path_mtu = IBV_MTU_4096;        // MTU: 4096 bytes
    attr.dest_qp_num = remoteInfo.qpNum;  // 对端 QP 编号
    attr.rq_psn = 0;                      // 接收包序列号起始值
    
    // 设置 Address Vector (对端路由信息)
    attr.ah_attr.is_global = 1;
    attr.ah_attr.dlid = remoteInfo.lid;
    attr.ah_attr.sl = 0;                  // Service Level (QoS)
    attr.ah_attr.src_path_bits = 0;
    attr.ah_attr.port_num = ibPort;
    attr.ah_attr.grh.dgid = remoteInfo.gid;
    attr.ah_attr.grh.flow_label = 0;
    attr.ah_attr.grh.sgid_index = localGidIndex;
    attr.ah_attr.grh.hop_limit = 0xFF;   // 最大跳数
    attr.ah_attr.grh.traffic_class = 0;
    
    // Reliable Connection 路径信息
    attr.max_dest_rd_atomic = 16;          // 对端最大并发 RDMA 操作数
    attr.min_rnr_timer = 12;              // RNR (Receiver Not Ready) 超时
    
    ibv_modify_qp(qp, &attr,
        IBV_QP_STATE              |
        IBV_QP_AV                 |
        IBV_QP_PATH_MTU           |
        IBV_QP_DEST_QPN           |
        IBV_QP_RQ_PSN             |
        IBV_QP_MAX_DEST_RD_ATOMIC |
        IBV_QP_MIN_RNR_TIMER);
    // QP 现在可以接收数据了
    
    // ══════════════════════════════════════
    // Phase 8: RTR → RTS (Ready to Send)
    // ══════════════════════════════════════
    
    memset(&attr, 0, sizeof(attr));
    attr.qp_state = IBV_QPS_RTS;
    attr.timeout = 14;                     // 传输超时: 4.096 μs × 2^14 ≈ 67 ms
    attr.retry_cnt = 7;                    // 重试次数
    attr.rnr_retry = 7;                    // RNR 重试次数 (7 = 无限重试)
    attr.sq_psn = 0;                       // 发送包序列号起始值
    attr.max_rd_atomic = 16;               // 本端最大并发 RDMA 操作数
    
    ibv_modify_qp(qp, &attr,
        IBV_QP_STATE              |
        IBV_QP_TIMEOUT            |
        IBV_QP_RETRY_CNT          |
        IBV_QP_RNR_RETRY          |
        IBV_QP_SQ_PSN             |
        IBV_QP_MAX_QP_RD_ATOMIC);
    
    // QP 现在完全就绪！可以发送和接收数据了
    
    conn->qp = qp;
    conn->sendCq = sendCq;
    conn->recvCq = recvCq;
    conn->mr = mr;
    
    return ncclSuccess;
}
```

### 7.3 QP 状态机的完整流程

```
       ┌────────┐
       │ RESET  │  ← ibv_create_qp() 后的初始状态
       └───┬────┘
           │ ibv_modify_qp: 设置 PKey, Port, Access Flags
           ▼
       ┌────────┐
       │  INIT  │  ← 可以注册 MR, 发布 Receive WR
       └───┬────┘
           │ ibv_modify_qp: 设置 Dest QPN, Path MTU, AH
           ▼
       ┌────────┐
       │  RTR   │  ← 可以接收数据 (Ready to Receive)
       └───┬────┘
           │ ibv_modify_qp: 设置 Timeout, Retry, SQ_PSN
           ▼
       ┌────────┐
       │  RTS   │  ← 可以发送数据 (Ready to Send)
       └───┬────┘
           │
           ▼
       NCCL 通道就绪，可以执行数据传输
       
每个 QP 维护两个队列:
  ├── Send Queue (SQ): 存放要发送的 Work Requests
  └── Receive Queue (RQ): 存放预期要接收的 Work Requests

每个队列中的 WR 完成后:
  → 产生 CQE (Completion Queue Entry) 放入 CQ
  → NCCL 的进度线程 polling CQ 检查完成情况
```

---

## 八、GPUDirect RDMA 的数据路径

### 8.1 传统路径 vs GDR 路径

```
传统路径 (无 GPUDirect RDMA):
                                    
  GPU 0                                GPU 1
  ┌──────┐                            ┌──────┐
  │ 显存  │                            │ 显存  │
  └──┬───┘                            └──┬───┘
     │ PCIe                              │ PCIe
     ▼                                   ▲
  ┌──────┐     PCIe      ┌──────┐    ┌──────┐     PCIe      ┌──────┐
  │ Host │ ──────────→ │ Host │    │ Host │ ←────────── │ Host │
  │ 内存  │ (DMA)      │ 内存  │    │ 内存  │  (DMA)      │ 内存  │
  │(src) │            │(staging)│    │(staging)│            │(dst)  │
  └──┬───┘            └──┬───┘    └──┬───┘            └──┬───┘
     │                    │           │                    │
     └────── CPU 拷贝 ───┘           └──── CPU 拷贝 ───┘
     
  数据路径: GPU → PCIe → CPU → 内存 → CPU → PCIe → HCA → 网络
            → HCA → PCIe → CPU → 内存 → CPU → PCIe → GPU
  
  总拷贝: 4 次 DMA + 2 次 CPU 参与
  延迟: ~10-20 μs 额外开销

════════════════════════════════════════════════════════════

GPUDirect RDMA 路径:

  GPU 0                                                  GPU 1
  ┌──────┐                                              ┌──────┐
  │ 显存  │                                              │ 显存  │
  └──┬───┘                                              └──┬───┘
     │ PCIe (PCIe BAR 直接映射)                             │ PCIe
     ▼                                                     ▲
  ┌──────┐           IB/RoCE 网络              ┌──────┐
  │  HCA │ ══════════════════════════════════ │  HCA │
  │(mlx5)│         (RDMA Write/Read)          │(mlx5)│
  └──────┘                                    └──────┘
  
  数据路径: GPU → PCIe → HCA → 网络 → HCA → PCIe → GPU
  
  总拷贝: 2 次 DMA (GPU↔HCA)，0 次 CPU 参与
  延迟: ~2-5 μs
  
  关键技术:
  - HCA 通过 PCIe BAR 页表直接映射 GPU 显存
  - CPU 不参与数据搬运
  - 内核驱动 mlx5_ib + nvidia-peermem 模块协同工作
```

### 8.2 GPUDirect RDMA 的内核态注册过程

```
ibv_reg_mr(pd, gpuBuffer, size, access_flags)
       │
       ▼
  libibverbs.so → 内核态 ibv_reg_mr
       │
       ▼
  mlx5_ib 驱动 → ib_umem_get()
       │
       ├── pin_user_pages_fast(gpuBuffer, size)
       │   → 将 GPU 显存页 pin 到物理内存
       │   → 通过 nvidia-peermem 模块的回调:
       │     nv_peermem_get_pages()
       │     → 返回 GPU 显存的 DMA 地址
       │
       ├── 构建 MTT (Memory Translation Table)
       │   → 将 GPU 显存的物理地址写入 HCA 的 Page Table
       │   → HCA 之后可以通过 DMA 地址直接读写 GPU 显存
       │
       └── 返回 lkey, rkey
           → lkey: 本地 HCA 用于地址翻译的 Key
           → rkey: 远端 HCA 用于 RDMA 操作的 Key

GPU 端:
  nvidia-peermem.ko (或 nv_peer_mem.ko)
       │
       ├── 注册为 Linux 内核的 peer memory client
       │   (kernel: mm/hmm.c 或 infiniband/core/peer_mem.c)
       │
       ├── 当 mlx5_ib 调用 get_peer_dma_address() 时:
       │   → nvidia-peermem 通过 NVIDIA 驱动获取 GPU 显存的
       │     PCIe BAR 映射地址 (bus address)
       │
       └── 返回 DMA 地址给 mlx5_ib
           → mlx5_ib 将 DMA 地址写入 HCA 的 WQE
```

---

## 九、ncclCommInitRankSync —— 最终同步验证

### 9.1 All-Reduce 测试

```c
// src/init.cc

ncclResult_t ncclCommInitRankSync(struct ncclComm* comm) {
    
    // ══════════════════════════════════════
    // Step 1: 分配测试 buffer
    // ══════════════════════════════════════
    
    void* sendBuffer;
    void* recvBuffer;
    CUDACHECK(cudaMalloc(&sendBuffer, comm->buffSizes[0]));
    CUDACHECK(cudaMalloc(&recvBuffer, comm->buffSizes[0]));
    
    // ══════════════════════════════════════
    // Step 2: 执行一次 All-Reduce 测试
    // ══════════════════════════════════════
    
    // 每个 rank 用自己的 rank 号填充 sendBuffer
    CUDACHECK(cudaMemset(sendBuffer, comm->rank, TEST_SIZE));
    
    // 调用 NCCL 内部的 All-Reduce
    NCCLCHECK(ncclAllReduce(
        sendBuffer, 
        recvBuffer,
        TEST_SIZE / sizeof(float),
        ncclFloat,
        ncclSum,
        comm,
        cudaStreamDefault  // 使用默认 stream
    ));
    
    // 同步等待完成
    CUDACHECK(cudaStreamSynchronize(cudaStreamDefault));
    
    // 验证结果
    // All-Reduce(Sum) of [rank, rank, ...] 应该等于 [worldSize*(worldSize-1)/2, ...]
    float expected = (float)(comm->nRanks * (comm->nRanks - 1)) / 2.0f;
    float actual;
    CUDACHECK(cudaMemcpy(&actual, recvBuffer, sizeof(float), cudaMemcpyDeviceToHost));
    
    if (fabs(actual - expected) > 0.01f) {
        WARN("NCCL All-Reduce verification failed: expected %f, got %f", expected, actual);
        return ncclInternalError;
    }
    
    // ══════════════════════════════════════
    // Step 3: 标记 Communicator 就绪
    // ══════════════════════════════════════
    
    comm->initState = ncclSuccess;
    
    // 清理测试 buffer
    cudaFree(sendBuffer);
    cudaFree(recvBuffer);
    
    return ncclSuccess;
}
```

### 9.2 同步的时序保证

```
全部 16 个 rank 的同步点:

Rank 0:  ncclCommInitRankSync() → AllReduce 测试 → 等待完成 ──┐
Rank 1:  ncclCommInitRankSync() → AllReduce 测试 → 等待完成 ──┤
Rank 2:  ncclCommInitRankSync() → AllReduce 测试 → 等待完成 ──┤
  ...                                                          │
Rank 15: ncclCommInitRankSync() → AllReduce 测试 → 等待完成 ──┤
                                                                │
                           全部同步完成 ←────────────────────────┘
                                    │
                                    ▼
                           ncclCommInitRank() 返回
                                    │
                                    ▼
                           用户代码开始训练
```

---

## 十、环境变量对 NCCL Init 的影响

### 10.1 关键环境变量的精确作用点

```c
// 每个环境变量在 Init 的哪个阶段生效:

// ═══ Bootstrap 阶段 ═══
NCCL_COMM_ID           // 替代 ncclUniqueId 中的地址，用于 bootstrap
NCCL_BOOTSTRAP_VERBS   // 使用 IB verbs 而非 TCP 做 bootstrap（高版本 NCCL）
NCCL_BOOTSTRAP_IP_PORT // 指定 bootstrap 端口范围

// ═══ 拓扑发现阶段 ═══
NCCL_TOPO_FILE         // 自定义拓扑文件路径 (XML 格式)
NCCL_TOPO_DUMP_FILE    // dump 当前拓扑到文件（调试用）
NCCL_IGNORE_CPU_AFFINITY=1  // 忽略 CPU 亲和性对 NUMA 的影响

// ═══ 拓扑计算阶段 ═══
NCCL_MIN_NCHANNELS     // 最少通道数 (默认 1)
NCCL_MAX_NCHANNELS     // 最多通道数 (默认 32, 实际取决于拓扑)
NCCL_NSOCKS_PERTHREAD  // 每个 NET 线程使用的 Socket 数
NCCL_NSOCKS_PERCOMM    // 每个 Communicator 的 Socket 数
NCCL_SOCKET_NTHREADS   // Socket 线程数
NCCL_ALGO              // 强制指定算法: Ring / Tree / CollNet
NCCL_PROTO             // 强制指定协议: Simple / LL / LL128

// ═══ P2P 阶段 ═══
NCCL_P2P_LEVEL         // 限制 P2P 级别: SYS / PHB / PXB / P2P / LOC
NCCL_P2P_DISABLE=1     // 禁用 P2P
NCCL_SHM_DISABLE=1     // 禁用 SHM
NCCL_P2P_NET_CHUNKSIZE // P2P 网络分片大小

// ═══ IB/RDMA 阶段 ═══
NCCL_IB_DISABLE=1      // 禁用 IB，退化到 Socket
NCCL_NET_GDR_LEVEL     // GPUDirect RDMA 级别
  // 0: 禁用 GDR
  // 2: 仅 Socket 内 GPU→NIC 使用 GDR
  // 3: 仅跨 Socket 使用 GDR
  // 4: 始终使用 GDR
  // 5: 智能选择（默认）
NCCL_IB_HCA            // 指定 IB 设备: "=mlx5_0,mlx5_1"
NCCL_IB_GID_INDEX      // GID 索引 (RoCE v2 通常为 3)
NCCL_IB_TIMEOUT         // IB 超时 (指数: 4.096μs × 2^value)
NCCL_IB_RETRY_CNT       // IB 重试次数
NCCL_IB_SL              // IB Service Level (QoS)
NCCL_IB_TC              // Traffic Class
NCCL_NET_PLUGIN         // 网络插件路径

// ═══ CollNet / SHARP 阶段 ═══
NCCL_COLLNET_ENABLE=1   // 启用 CollNet (网络内聚合)
NCCL_SHARP_DISABLE=1    // 禁用 SHARP

// ═══ 调试和性能 ═══
NCCL_DEBUG=INFO         // 调试等级: VERSION / WARN / INFO / TRACE / GRAPH
NCCL_DEBUG_SUBSYS=INIT  // 仅显示 INIT 子系统的日志
NCCL_DEBUG_FILE=/tmp/nccl.log  // 日志输出到文件
```

### 10.2 NCCL_DEBUG=INFO 输出的实际示例

```bash
# 设置环境变量后运行:
export NCCL_DEBUG=INFO
export NCCL_DEBUG_SUBSYS=INIT
torchrun --nproc_per_node=8 --nnodes=2 --node_rank=0 train.py
```

```
# Rank 0 的输出 (节点 0):

nccl-comm-init: ncclCommInitRankFunc starting rank=0 nranks=16
nccl-bootstrap: ncclTransportInit starting, rank 0, nRanks 16
nccl-bootstrap: Connecting to peers via TCP
nccl-bootstrap: Rank 0 listening on 10.0.0.1:23457
nccl-bootstrap: Rank 0 received connection from rank 1
nccl-bootstrap: Rank 0 received connection from rank 2
...
nccl-bootstrap: All 16 ranks connected

nccl-topo: ncclTopoGetSystem starting
nccl-topo: Found 8 GPUs on this node
nccl-topo:   GPU 0: 0000:3b:00.0, NUMA 0, NVLink to GPU[1,2,3]
nccl-topo:   GPU 1: 0000:3e:00.0, NUMA 0, NVLink to GPU[0,2,3]
nccl-topo:   GPU 2: 0000:60:00.0, NUMA 0, NVLink to GPU[0,1,3]
nccl-topo:   GPU 3: 0000:63:00.0, NUMA 0, NVLink to GPU[0,1,2]
nccl-topo:   GPU 4: 0000:9b:00.0, NUMA 1, NVLink to GPU[5,6,7]
nccl-topo:   GPU 5: 0000:9e:00.0, NUMA 1, NVLink to GPU[4,6,7]
nccl-topo:   GPU 6: 0000:c0:00.0, NUMA 1, NVLink to GPU[4,5,7]
nccl-topo:   GPU 7: 0000:c3:00.0, NUMA 1, NVLink to GPU[4,5,6]
nccl-topo: Found 2 IB devices:
nccl-topo:   mlx5_0: 0000:3b:00.0, NUMA 0, 200 Gb/sec, GID_INDEX 3
nccl-topo:   mlx5_1: 0000:9b:00.0, NUMA 1, 200 Gb/sec, GID_INDEX 3
nccl-topo: NVSwitch detected: 2 switches

nccl-graph: ncclTopoCompute starting
nccl-graph: Searching ring for 16 GPUs
nccl-graph: Channel 0 ring: 0→1→2→3→4→5→6→7→15→14→13→12→11→10→9→8→0
nccl-graph: Channel 0 tree: 0→{1,8}, 1→{2,9}, 2→{3,10}...
nccl-graph: Channel 0: intra-node P2P (NVLink), inter-node NET (IB, mlx5_0→mlx5_1)
nccl-graph: Found 8 channels (NCCL_MAX_CHANNELS limit: 32)

nccl-transport: ncclTransportP2pSetup
nccl-transport: P2P between GPU 0 ↔ GPU 1: NVLink, 600 GB/s
nccl-transport: P2P between GPU 0 ↔ GPU 8: NET (IB mlx5_0→mlx5_0), 200 Gbps
nccl-transport: GPUDirect RDMA enabled (level 5)
nccl-transport: Registering GPU buffer 0x7f..., size=1048576 for RDMA
nccl-transport: QP created: QP num=1234, send CQ, recv CQ

nccl-transport: ncclTransportNetSetup
nccl-net: Using IB plugin (libnccl-net.so / mlx5)
nccl-net: Device 0: mlx5_0, speed=200000, port=1
nccl-net: Device 1: mlx5_1, speed=200000, port=1
nccl-net: Creating QP for connection to rank 8
nccl-net:   QP state: RESET → INIT → RTR → RTS
nccl-net:   RDMA MR registered: lkey=0x1234, rkey=0x5678

nccl-sync: ncclCommInitRankSync
nccl-sync: AllReduce test: rank 0, expected sum=120.0
nccl-sync: AllReduce test passed!

nccl: ncclCommInitRank completed successfully
nccl:   rank=0, nRanks=16, nChannels=8
nccl:   algo=Ring+Tree, proto=Simple
nccl:   commHash=0x1a2b3c4d
```

---

## 十一、从 NCCL Init 完成到训练循环的衔接

```python
# 用户代码视角

# 1. NCCL Init 完成
torch.distributed.init_process_group(backend='nccl')
#   → ncclCommInitRank() 返回 ncclComm_t

# 2. 创建模型并包装为 DDP
model = MyModel().cuda()
model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[local_rank])
#   → DDP 内部为每个参数创建 gradient buffer
#   → buffer 注册到 NCCL communicator

# 3. 训练循环
for batch in dataloader:
    # 3a. Forward pass
    loss = model(batch)
    
    # 3b. Backward pass
    loss.backward()
    #   → 每个参数的 .grad 被计算
    
    # 3c. AllReduce gradients (DDP 自动插入)
    #   → 调用 ncclAllReduce(grad_buffer, ...)
    #   → NCCL 使用之前建立的 Ring/Tree 通道
    #   → IB QP 上的 RDMA Write 操作
    
    # 3d. 更新参数
    optimizer.step()
```

### 11.1 DDP 的 AllReduce Hook 注册

```cpp
// torch/csrc/distributed/autograd/engine/dist_engine.cpp (简化)

void DistributedDataParallel::register_hooks() {
    // 为每个参数注册 "post-accumulate gradients" hook
    for (auto& param : parameters_) {
        auto hook = param.register_post_accumulate_grad_hook([this, &param]() {
            // 当该参数的梯度计算完成后触发
            this->allreduce_hooks(param);
        });
    }
}

void DistributedDataParallel::allreduce_hooks(Parameter& param) {
    // 使用 bucket 策略减少通信次数
    auto& bucket = find_or_create_bucket(param);
    bucket.pending_params--;
    
    if (bucket.pending_params == 0) {
        // 该 bucket 中所有参数的梯度都已就绪
        // 发起一次 AllReduce
        comm_->allReduce(bucket.buffer, bucket.buffer, 
                         bucket.numel, ncclFloat, ncclSum);
    }
}
```

### 11.2 ncclAllReduce 的数据路径

```
AllReduce (Ring 算法) 的数据路径:

Step 0:  每个 GPU 有 1/N 的数据
         GPU0: [A0]  GPU1: [A1]  GPU2: [A2]  GPU3: [A3]

Step 1:  Reduce-Scatter (N-1 步)
         GPU0 发送 A0 的 1/4 到 GPU1 (通过 NVLink/IB)
         GPU1 发送 A1 的 1/4 到 GPU2
         GPU2 发送 A2 的 1/4 到 GPU3
         GPU3 发送 A3 的 1/4 到 GPU0
         同时本地累加接收到的数据
         ...重复 N-1 步...
         
         结果: 每个 GPU 持有全局 sum 的 1/N
         GPU0: [sum(chunk0)]  GPU1: [sum(chunk1)] ...

Step 2:  AllGather (N-1 步)
         GPU0 发送 sum(chunk0) 到 GPU1
         GPU1 转发 sum(chunk0) 到 GPU2
         ...环形传播...
         
         结果: 每个 GPU 持有完整的全局 sum

每个 Step 的实际传输:
  ├── NCCL Kernel (在 GPU 上运行的 CUDA Kernel)
  │   ├── 将数据从 Global Memory 读入 Register
  │   ├── 如果是 Reduce 阶段: 执行 float4 加法
  │   ├── 将数据写入 Send Ring Buffer (GPU 显存)
  │   └── 写入 Tail Flag (通知传输线程)
  │
  ├── Transport Thread (NCCL 的 CPU 线程)
  │   ├── 轮询 Tail Flag (GPU→CPU 通知)
  │   ├── 准备 IB Work Request (WR)
  │   │   ├── wr.opcode = IBV_WR_RDMA_WRITE
  │   │   ├── wr.wr.rdma.remote_addr = 对端 GPU buffer 地址
  │   │   ├── wr.wr.rdma.rkey = 对端 MR 的 rkey
  │   │   └── wr.sg_list = [{addr: local_gpu_buffer, length: chunk_size, lkey: ...}]
  │   ├── ibv_post_send(qp, &wr)  → HCA 立即开始 DMA
  │   └── ibv_poll_cq(cq, ...)    → 检查完成
  │
  └── GPU Kernel (接收端)
      ├── 通过 Tail Flag 检测数据到达
      ├── 从 Recv Ring Buffer 读取数据
      └── 如果是 Reduce 阶段: 执行累加
```

---

## 总结：NCCL Init 的完整状态机

```
┌─────────────────────────────────────────────────────────────┐
│                     NCCL Init 完整状态机                       │
│                                                              │
│  [Python] init_process_group(backend='nccl')                 │
│       │                                                      │
│       ▼                                                      │
│  [1] Rendezvous                                              │
│       ├── TCPStore 建立 (MASTER_ADDR:MASTER_PORT)            │
│       ├── ncclUniqueId 广播                                  │
│       └── 所有 rank 就绪                                      │
│       │                                                      │
│       ▼                                                      │
│  [2] Bootstrap                                               │
│       ├── 通过 ncclId 中的 TCP 地址建立控制通道                  │
│       ├── Rank 0 收集所有 rank 的 bootstrap 地址               │
│       └── 全连接 TCP 拓扑                                     │
│       │                                                      │
│       ▼                                                      │
│  [3] 拓扑发现 (ncclTopoGetSystem)                             │
│       ├── 扫描 /sys/bus/pci/devices/                         │
│       ├── 读取 NVML (NVLink 拓扑)                            │
│       ├── 读取 sysfs (IB 设备, NUMA, PCIe 拓扑)              │
│       └── 构建 ncclTopoSystem 数据结构                        │
│       │                                                      │
│       ▼                                                      │
│  [4] 拓扑计算 (ncclTopoCompute)                               │
│       ├── 搜索 Ring 通道 (DFS + 贪心)                         │
│       ├── 搜索 Tree 通道                                      │
│       ├── 每条边选择传输方式 (P2P > SHM > NET)                 │
│       └── 确定通道数 (通常 8~32 个)                            │
│       │                                                      │
│       ▼                                                      │
│  [5] P2P 建立 (ncclTransportP2pSetup)                        │
│       ├── cudaDeviceCanAccessPeer() 验证                     │
│       ├── cudaDeviceEnablePeerAccess()                       │
│       ├── cudaIpcGetMemHandle() + cudaIpcOpenMemHandle()     │
│       ├── 分配 Ring Buffer (GPU 显存)                        │
│       └── 创建 IPC Event 用于同步                             │
│       │                                                      │
│       ▼                                                      │
│  [6] NET 建立 (ncclTransportNetSetup)                        │
│       ├── 加载 IB 插件 (libnccl-net.so)                      │
│       ├── ibv_open_device()                                  │
│       ├── ibv_alloc_pd()                                     │
│       ├── ibv_create_cq()                                    │
│       ├── ibv_create_qp() → QP (RESET 状态)                  │
│       ├── QP: RESET → INIT → RTR → RTS                      │
│       ├── ibv_reg_mr() (GPUDirect RDMA)                      │
│       ├── 交换 QPN/LID/GID/RKEY (通过 Bootstrap)             │
│       └── 所有 IB QP 就绪                                    │
│       │                                                      │
│       ▼                                                      │
│  [7] 同步验证 (ncclCommInitRankSync)                          │
│       ├── 执行一次 AllReduce 测试                              │
│       ├── 验证结果正确性                                       │
│       └── 全部 rank 同步完成                                   │
│       │                                                      │
│       ▼                                                      │
│  [8] init_process_group() 返回                               │
│       │                                                      │
│       ▼                                                      │
│  [9] DDP 包装 + 训练循环                                      │
│       ├── register_hook on each parameter                    │
│       ├── backward() → gradient ready → AllReduce            │
│       └── ncclAllReduce() 使用已建立的 Ring/Tree/NET 通道      │
└─────────────────────────────────────────────────────────────┘
```

整个 NCCL Init 过程，在正常情况下（8 GPU × 2 节点，IB 网络），耗时大约 **2-10 秒**。主要时间花在拓扑发现和 IB QP 建立上。如果集群规模很大（数百个节点），Bootstrap 和拓扑交换阶段可能需要更长时间，此时需要调整 `NCCL_TIMEOUT` 相关参数。
