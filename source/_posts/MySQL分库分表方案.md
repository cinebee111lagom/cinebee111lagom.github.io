---
title: MySQL 分库分表方案
date: 2026-09-08 03:30:00
tags:
  - MySQL
  - 分库分表
  - ShardingSphere
  - 架构
categories:
  - MySQL
---

## 一、为什么需要分库分表？

当单表数据量达到 **千万级** 或单库压力过大时，会出现：

| 问题 | 表现 |
|------|------|
| 查询变慢 | 索引 B+ 树层数增加，IO 放大 |
| 写入瓶颈 | 锁竞争激烈，主从延迟加剧 |
| 存储瓶颈 | 单机磁盘/内存容量见顶 |
| 连接数耗尽 | 单库连接池上限不够用 |

---

## 二、垂直拆分 vs 水平拆分

### 垂直分库
按 **业务模块** 拆到不同数据库实例：

```
MySQL实例1 (用户库)  →  user_db.user_info
                        user_db.user_address

MySQL实例2 (订单库)  →  order_db.order_master
                        order_db.order_detail

MySQL实例3 (商品库)  →  product_db.product_info
                        product_db.product_stock
```

### 垂直分表
将一张宽表按 **访问频率** 拆分为多张表：

```
user_info (热字段)         user_detail (冷字段)
├── id (PK)                ├── id (PK)
├── name                   ├── education
├── email                  ├── biography
└── phone                  └── created_at
通过 1:1 关联查询
```

### 水平分库
同一张表的数据按规则分散到 **多个数据库实例**：

```
order_db_0  →  order_master (id % 4 == 0 的数据)
order_db_1  →  order_master (id % 4 == 1 的数据)
order_db_2  →  order_master (id % 4 == 2 的数据)
order_db_3  →  order_master (id % 4 == 3 的数据)
```

### 水平分表
同一张表的数据按规则拆到 **同一库的多张表**：

```
order_db → order_master_0 (id % 4 == 0)
           order_master_1 (id % 4 == 1)
           order_master_2 (id % 4 == 2)
           order_master_3 (id % 4 == 3)
```

---

## 三、常见分片键（Sharding Key）选择

这是分库分表中 **最关键的决策**，直接决定了路由效率和查询能力。

| 分片键 | 适用场景 | 优点 | 缺点 |
|--------|---------|------|------|
| 用户 ID | C 端系统（电商、社交） | 同一用户数据落在同一分片，避免跨库查询 | 非用户维度查询需广播 |
| 订单 ID | 订单系统 | 分布均匀 | 按用户查订单需要广播 |
| 时间 | 日志、流水 | 天然有序，易归档冷数据 | 热点写入集中在最后一个分片 |
| 地区 ID | 本地生活服务 | 同城数据聚合 | 数据倾斜严重 |

### 分片键选取原则

```
1. 高频查询条件必须包含分片键（避免全分片扫描）
2. 数据分布尽量均匀（避免热点）
3. 尽量让关联查询落在同一分片（如：同一用户的订单和地址）
```

---

## 四、分片路由算法

### 1. 取模（Hash）
```java
int dbIndex = userId.hashCode() % 4;
int tableIndex = userId.hashCode() % 8;
```
- 优点：分布均匀
- 缺点：扩容需要迁移数据

### 2. 范围分片（Range）
```
表0: order_id ∈ [0,       1000万)
表1: order_id ∈ [1000万,  2000万)
表2: order_id ∈ [2000万,  3000万)
```
- 优点：天然有序，扩容简单
- 缺点：容易写入热点

### 3. 一致性哈希
```
      ┌── Node A
Key ──┤── Node B    （环形哈希空间）
      └── Node C
```
- 优点：扩容只影响相邻节点，迁移数据少
- 缺点：实现复杂，需虚拟节点保证均匀

### 4. 映射表（路由表）
```sql
-- 独立的路由库
user_id_range | db_index | table_index
[1-10000]     | 0        | 0
[10001-20000] | 0        | 1
[20001-30000] | 1        | 0
```
- 优点：灵活，可动态调整
- 缺点：多一次查询开销，需保证路由表高可用

---

## 五、分库分表带来的问题及解决方案

### 1. 分布式 ID 生成

不能依赖自增主键了，常用方案：

| 方案 | 实现 | 特点 |
|------|------|------|
| **雪花算法（Snowflake）** | 41位时间戳 + 10位机器 + 12位序列号 | 趋势递增，性能高，64位 long |
| **号段模式（Leaf）** | 从 DB 批量获取号段缓存在内存 | 美团 Leaf 方案，可用性高 |
| **UUID** | 128位随机字符串 | 简单但无序，不适合做主键 |
| **Redis 自增** | INCR 命令 | 有序，但引入 Redis 依赖 |

### 2. 跨分片查询

```sql
-- 场景：查询某个商品的所有订单（商品ID不是分片键）
-- 必须广播到所有分片并合并结果
SELECT * FROM order_0 WHERE product_id = 123
UNION ALL
SELECT * FROM order_1 WHERE product_id = 123
UNION ALL
SELECT * FROM order_2 WHERE product_id = 123
UNION ALL
SELECT * FROM order_3 WHERE product_id = 123
```

**解决方案：**
- **基因法**：在 ID 中嵌入分片信息，使其能自我路由
- **异构索引表**：冗余一张以 `product_id` 为分片键的影子表
- **宽表/搜索引擎**：将需要多维查询的数据同步到 Elasticsearch

### 3. 跨分片 Join

```
❌ SELECT * FROM order o JOIN user u ON o.user_id = u.id

✅ 方案一：相同分片键的表放在同一库（内聚）
✅ 方案二：应用层组装（查出 order 后再查 user）
✅ 方案三：数据冗余（将 user_name 冗余到 order 表）
```

### 4. 分布式事务

```java
// 方案一：TCC（Try-Confirm-Cancel）
try {
    orderService.tryCreate(order);   // 预留资源
    stockService.tryDeduct(skuId);   // 预留库存
} catch (Exception e) {
    orderService.cancel(order);      // 回滚
    stockService.restore(skuId);     // 恢复库存
}

// 方案二：基于消息的最终一致性（推荐）
1. 本地事务写入 order + 写消息到本地消息表
2. 异步发送消息到 MQ
3. 消费端扣减库存，成功后 ACK

// 方案三：使用 Seata 等分布式事务框架
```

### 5. 分页 & 排序

```sql
-- 跨分片分页（取第 21~30 条，按时间排序）
-- 问题：每个分片都要取前 30 条再合并排序取前 30 条

-- 方案一：禁止跳页，只允许上下翻（游标分页）
SELECT * FROM order_x 
WHERE create_time < :lastCreateTime 
ORDER BY create_time DESC 
LIMIT 10;

-- 方案二：各分片取 limit(N+M) 合并后截取
-- 方案三：将排序字段冗余到单独的分片聚合表
```

### 6. 扩容（二次分片）

```
方案一：成倍扩容（2 → 4 → 8）
  每次翻倍，数据只需迁移一半，路由规则改动最小

方案二：提前规划足够多的逻辑分片
  比如一开始规划 1024 个逻辑表，映射到 4 个物理库
  扩容时只改映射关系，不需要 rehash 全部数据
```

---

## 六、主流中间件对比

| 维度 | **ShardingSphere-JDBC** | **ShardingSphere-Proxy** | **MyCat** |
|------|------------------------|--------------------------|-----------|
| 架构 | 嵌入应用，JDBC 层拦截 | 独立进程，模拟 MySQL 协议 | 独立进程，模拟 MySQL 协议 |
| 语言 | Java only | Any | Any |
| 性能 | 无网络开销，性能略高 | 多一跳网络 | 多一跳网络 |
| 运维 | 无独立组件 | 需部署 Proxy 集群 | 需部署实例 |
| 功能 | 分片、读写分离、分布式事务、影子库 | 同左 + 可被非 Java 使用 | 分片、读写分离 |
| 生态 | Apache 顶级项目，活跃 | 同左 | 社区趋于停滞 |

### ShardingSphere-JDBC 配置示例

```yaml
# application.yml (Spring Boot)
spring:
  shardingsphere:
    datasource:
      names: ds0, ds1
      ds0:
        type: com.zaxxer.hikari.HikariDataSource
        jdbc-url: jdbc:mysql://host1:3306/db0
        username: root
        password: xxx
      ds1:
        type: com.zaxxer.hikari.HikariDataSource
        jdbc-url: jdbc:mysql://host2:3306/db1
        username: root
        password: xxx
    rules:
      sharding:
        tables:
          t_order:
            actual-data-nodes: ds$->{0..1}.t_order_$->{0..3}
            database-strategy:
              standard:
                sharding-column: user_id
                sharding-algorithm-name: db-hash
            table-strategy:
              standard:
                sharding-column: order_id
                sharding-algorithm-name: table-hash
        sharding-algorithms:
          db-hash:
            type: HASH_MOD
            props:
              sharding-count: 2
          table-hash:
            type: HASH_MOD
            props:
              sharding-count: 4
```

---

## 七、架构决策参考

```
数据量评估
  │
  ├── < 500 万行 → 单表 + 合适索引即可
  │
  ├── 500万 ~ 2000万 → 分表（同库多表） + 读写分离
  │
  ├── 2000万 ~ 1亿 → 分库分表
  │
  └── > 1亿 → 分库分表 + 冷热分离 + 搜索引擎辅助

能不分就不分，能少分就少分。
```

**核心原则：**
1. **垂直拆分优先**：先按业务拆库，简单有效
2. **水平拆分是最后手段**：带来巨大的复杂性成本
3. **分片键的选择决定成败**：选错分片键后期极其痛苦
4. **提前规划好扩容方案**：首次实施就考虑未来的扩展路径
5. **配套基建要跟上**：分布式 ID、分布式事务、数据迁移工具、监控报警
