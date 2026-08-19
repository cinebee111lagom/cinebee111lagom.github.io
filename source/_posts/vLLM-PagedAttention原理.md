---
title: vLLM PagedAttention 原理
date: 2026-09-08 07:45:00
tags:
  - vLLM
  - PagedAttention
  - LLM
  - GPU
categories:
  - GPU
---

## 一、背景问题：KV Cache 的内存瓶颈

LLM 推理采用自回归解码，每生成一个 token 都需要缓存之前所有 token 的 Key 和 Value 向量（即 **KV Cache**）。在 serving 场景下，这是最主要的内存消耗来源。

传统框架（如 HuggingFace Transformers、DeepSpeed-FastChat）的做法是：

```
为每个请求预分配一块 连续内存，大小 = max_seq_len × num_layers × num_heads × head_dim × 2(K+V) × dtype_size
```

这带来两个严重的内存浪费：

| 浪费类型 | 来源 |
|---|---|
| **预留浪费（Reservation）** | 按最大序列长度分配，但实际生成通常远短于此 |
| **碎片化（Fragmentation）** | 要求物理内存连续，请求结束后留下不规则的空洞 |

结果：**在典型负载下，60%–80% 的显存被浪费**，GPU 利用率极低。

---

## 二、核心思想：操作系统分页机制

PagedAttention 将操作系统中 **虚拟内存 + 分页** 的经典思想迁移到 KV Cache 管理上。

### 2.1 关键概念映射

| 操作系统 | PagedAttention |
|---|---|
| 虚拟页（Virtual Page） | 逻辑 KV Block（一个 block 包含固定数量 token 的 KV 向量） |
| 物理页帧（Physical Frame） | 物理 KV Block（GPU 显存中的实际存储单元） |
| 页表（Page Table） | Block Table（记录 logical block → physical block 的映射） |
| 分页（Paging） | 一个请求的 KV Cache 按 block 粒度分配，不要求物理连续 |

### 2.2 内存布局对比

**传统方式（连续分配）：**
```
请求 A:  [████████████████████████__________]  ← 预分配到最大长度，尾部浪费
请求 B:  [██████████________________________]  ← 内部碎片
请求 C:  [████████████████__________________]  ← 空洞无法被其他请求利用

GPU 显存: [A A A A A A A A A A waste waste | B B B B waste waste waste... | C C ...]
```

**PagedAttention（分页分配）：**
```
逻辑视图（每个请求）:
  请求 A: [Block0] [Block1] [Block2]         ← 按需增长
  请求 B: [Block0] [Block1]
  请求 C: [Block0] [Block1] [Block2] [Block3]

物理视图（GPU 显存，block pool）:
  [A0] [B0] [C0] [A1] [C1] [B1] [A2] [C2] [空闲] [空闲] [C3] ...
  ← 物理位置可以任意，靠 block table 索引
```

---

## 三、Attention 计算如何适配

传统 attention 要求 K、V 在内存中连续存放，而 PagedAttention 将其拆分成非连续的 block。核心修改在 attention kernel 中：

```
对于每个 query token q_i:
  1. 通过 block table 查找该请求所有逻辑 block 对应的物理 block 地址
  2. 逐 block 加载 K, V
  3. 分块计算 q_i 与每个 block 的 attention score
  4. 使用 online softmax（类似 FlashAttention 的增量归一化）合并各 block 的结果
```

伪代码：

```python
def paged_attention(query, key_cache, value_cache, block_table, context_len):
    block_size = key_cache.block_size  # 每个 block 存多少 token
    num_blocks = ceil(context_len / block_size)
    
    max_score = -inf
    exp_sum = 0
    output = zeros(head_dim)
    
    for logical_idx in range(num_blocks):
        # 核心：通过 block table 做间接寻址
        physical_block = block_table[logical_idx]
        
        # 从非连续的物理 block 中加载 K, V
        k = key_cache[physical_block]    # shape: (block_size, head_dim)
        v = value_cache[physical_block]
        
        # 分块计算 attention score
        scores = query @ k.T / sqrt(head_dim)
        
        # Online softmax（增量归一化，无需拼接所有 block 的 score）
        block_max = max(scores)
        new_max = max(max_score, block_max)
        
        exp_sum = exp_sum * exp(max_score - new_max) + sum(exp(scores - new_max))
        output = output * exp(max_score - new_max) + exp(scores - new_max) @ v
        max_score = new_max
    
    output = output / exp_sum
    return output
```

关键点：**attention 计算本身不受影响**，只是 K/V 的物理寻址方式从连续偏移变成了 block table 间接寻址。

---

## 四、Copy-on-Write：跨请求共享 KV Cache

PagedAttention 的另一个杀手级特性：**不同请求的逻辑 block 可以指向同一个物理 block**，并通过引用计数管理生命周期。

### 应用场景

**1. Parallel Sampling（并行采样）**

用户请求"生成 4 个不同回答"：

```
Prompt 处理阶段（共享）:
  物理 Block Pool: [..., P0, P1, P2, ...]
  
  Sample 1 block_table: [P0, P1, P2]  ← ref_count: 4
  Sample 2 block_table: [P0, P1, P2]  ← 同上
  Sample 3 block_table: [P0, P1, P2]  ← 同上
  Sample 4 block_table: [P0, P1, P2]  ← 同上

生成阶段（写时复制）:
  当 Sample 1 需要在 Block2 后追加新 token 时:
    1. 对 P2 执行 copy-on-write → 分配新物理块 P2'
    2. Sample 1 的 block_table[2] = P2'
    3. P2 的 ref_count -= 1
```

**2. Beam Search**

多个 beam 共享公共前缀的 KV Cache，只在分支点执行 CoW。

内存节省示例（4 个 parallel sample，prompt 1000 tokens，生成 200 tokens）：

| 方案 | Prompt KV 内存 | 总 KV 内存 |
|---|---|---|
| 无共享 | 4 × prompt | 4 × (prompt + gen) |
| PagedAttention + CoW | 1 × prompt | 1 × prompt + 4 × gen |

---

## 五、实现细节

### 5.1 Block Table 数据结构

```
每个请求维护一张 block table:

block_table[seq_id] = [
    (physical_block_id, is_shared, token_count),
    (physical_block_id, is_shared, token_count),
    ...
]

GPU 上以 tensor 形式存储，供 kernel 索引:
  block_tables_tensor: shape = [max_batch_size, max_num_blocks_per_seq], dtype = int32
```

### 5.2 Block 分配器

```python
class BlockAllocator:
    def __init__(self, num_blocks, block_size):
        self.free_blocks = list(range(num_blocks))  # 空闲物理 block 链表
        self.ref_count = [0] * num_blocks            # 引用计数
    
    def allocate(self):
        """分配一个空闲物理 block"""
        return self.free_blocks.pop()
    
    def free(self, physical_block_id):
        """释放物理 block（引用计数归零时才真正回收）"""
        self.ref_count[physical_block_id] -= 1
        if self.ref_count[physical_block_id] == 0:
            self.free_blocks.append(physical_block_id)
    
    def copy_on_write(self, physical_block_id):
        """写时复制：分配新 block，拷贝内容，更新引用计数"""
        new_block = self.allocate()
        copy_block(physical_block_id, new_block)
        self.ref_count[physical_block_id] -= 1
        self.ref_count[new_block] = 1
        return new_block
```

### 5.3 内存管理策略

```
GPU 显存布局:
┌──────────────────────────────────────────────┐
│  模型权重 (固定)                               │
├──────────────────────────────────────────────┤
│  Activation Memory / Workspace (计算临时空间)   │
├──────────────────────────────────────────────┤
│  KV Cache Block Pool (剩余显存全部划为 block)   │
│  [Block0] [Block1] [Block2] ... [Block N-1]  │
└──────────────────────────────────────────────┘

num_gpu_blocks = (total_gpu_memory - model_memory - activation_memory) // block_memory
```

---

## 六、性能收益

来自 vLLM 论文（SOSP 2023）的关键数据：

| 指标 | 传统系统 | vLLM (PagedAttention) |
|---|---|---|
| KV Cache 内存利用率 | ~20-40% | ~96%+ |
| 吞吐量提升 | baseline | **2-4×** |
| 支持的最大并发数 | 受碎片限制 | 显著提升 |

内存浪费对比（论文图示化）：

```
传统系统内存浪费分布:
  ┌─────────────────────────────────────────┐
  │████░░░░████░░████░░░░████░░░░████░░░░░░│
  │█=使用  ░=浪费(预留+碎片)                    │
  └─────────────────────────────────────────┘
  浪费率: ~60-80%

PagedAttention:
  ┌─────────────────────────────────────────┐
  │█████████████████████████████████████░░░░│
  └─────────────────────────────────────────┘
  浪费率: <4% (仅最后一个 block 的内部碎片)
```

---

## 七、总结

PagedAttention 的核心贡献可以用三句话概括：

1. **分页管理**：将 KV Cache 按固定大小的 block 分配，通过 block table 做逻辑到物理的映射，消除连续内存要求带来的碎片化
2. **按需增长**：像操作系统按需分页一样，每个请求只分配当前需要的 block 数量，消除预留浪费
3. **共享机制**：通过 Copy-on-Write + 引用计数，让多个请求共享公共前缀的 KV Cache，极大节省并行场景的内存

这一设计将 OS 中经过数十年验证的虚拟内存思想成功迁移到 GPU 推理场景，成为当前 LLM serving 基础设施的标准做法。
