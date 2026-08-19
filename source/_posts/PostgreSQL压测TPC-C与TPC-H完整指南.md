---
title: PostgreSQL压测TPC-C与TPC-H完整指南
date: 2026-09-08 01:15:00
tags:
  - PostgreSQL
  - TPC-C
  - TPC-H
  - 压测
categories:
  - PostgreSQL
---

---

## 一、两个标准的本质区别

| 维度 | TPC-C | TPC-H |
|------|-------|-------|
| **测试类型** | OLTP（在线事务处理） | OLAP（在线分析处理） |
| **关注点** | 高并发短事务、吞吐量 | 复杂查询、大数据量扫描 |
| **核心指标** | tpmC（每分钟事务数） | QphH（每小时复合查询性能） |
| **数据模型** | 仓库/订单/库存（5张核心表） | 订单/零件/供应商/客户（8张核心表） |
| **典型操作** | INSERT/UPDATE/SELECT 单行 | 大表 JOIN、GROUP BY、子查询 |
| **并发特点** | 大量短事务、高频争用 | 少量复杂查询、长时间运行 |

---

## 二、TPC-C 压测

### 2.1 工具选择

常用开源工具：

```
1. pgbench        — PostgreSQL 自带，可模拟 TPC-C 类负载
2. HammerDB       — 图形化+CLI，原生支持 TPC-C 标准
3. BenchmarkSQL   — Java 实现，严格遵循 TPC-C 规范
```

### 2.2 使用 pgbench（快速上手）

```bash
# 初始化（-i 创建默认 schema，-s 指定 scale factor，即仓库数）
pgbench -i -s 100 postgres
# -s 100 表示 100 个仓库，约 10GB 数据量

# 运行压测（-c 并发数 -j 线程数 -T 持续秒数 -R 每秒目标事务数）
pgbench -c 64 -j 8 -T 300 -P 10 postgres
# -P 10 每10秒打印一次进度

# 使用自定义 TPC-C 风格脚本
pgbench -c 64 -j 8 -T 300 -f tpc-c_script.sql postgres
```

**pgbench 自带的内置事务模式说明：**
```bash
# 内置简单模式（默认）
pgbench -c 32 -T 300 postgres

# 内置 TPC-B 类模式（更贴近 TPC-C）
pgbench -c 32 -T 300 -N postgres
# -N：不使用简单更新，模拟更真实的混合负载
```

### 2.3 使用 BenchmarkSQL（严格 TPC-C）

```bash
# 1. 下载
git clone https://github.com/benchmarksql/benchmarksql.git
cd benchmarksql

# 2. 修改配置文件
cat > config/postgres.properties << 'EOF'
db=postgres
driver=org.postgresql.Driver
conn=jdbc:postgresql://localhost:5432/postgres
user=postgres
password=yourpassword
warehouses=100           # 仓库数
terminals=64             # 终端/并发数
runMins=5                # 运行分钟数
limitTxnsPerMin=0        # 0=不限制
EOF

# 3. 创建表并加载数据
./runSQL.sh config/postgres.properties sqlTableCreates.sql
./runLoader.sh config/postgres.properties

# 4. 创建索引和外键
./runSQL.sh config/postgres.properties sqlIndexCreates.sql

# 5. 运行测试
./runBenchmark.sh config/postgres.properties
```

### 2.4 使用 HammerDB

```bash
# 安装
wget https://github.com/TPC-Council/HammerDB/releases/download/v4.9/HammerDB-4.9-Linux.tar.gz
tar xzf HammerDB-4.9-Linux.tar.gz

# CLI 模式自动执行
cat > hammerdb_tpcc.tcl << 'EOF'
dbset db pg
diset connection pg_host localhost
diset connection pg_port 5432
diset connection pg_user postgres
diset connection pg_pass yourpassword
diset connection pg_dbase postgres

diset tpcc pg_count_ware 100
diset tpcc pg_num_vu 64
diset tpcc pg_driver timed
diset tpcc pg_rampup 2
diset tpcc pg_duration 5

buildschema
vudestory
vuset vu 64
vucreate
tcstart
vurun
tcstop
EOF

./hammerdbcli auto hammerdb_tpcc.tcl
```

### 2.5 TPC-C 关键 PostgreSQL 调优参数

```sql
-- postgresql.conf 关键配置

-- 连接与内存
max_connections = 200
shared_buffers = '16GB'              -- 建议物理内存的 25%
effective_cache_size = '48GB'        -- 物理内存的 75%
work_mem = '256MB'                   -- 每个排序/哈希操作
maintenance_work_mem = '2GB'

-- WAL 与写入
wal_level = minimal                  -- 压测时可降低（需重启）
max_wal_size = '16GB'
wal_buffers = '64MB'
checkpoint_completion_target = 0.9
synchronous_commit = off             -- 压测时关闭同步提交（不推荐生产）

-- 优化器
random_page_cost = 1.1               -- SSD 环境
effective_io_concurrency = 200       -- SSD 环境
enable_seqscan = on

-- 并行
max_worker_processes = 16
max_parallel_workers_per_gather = 4
max_parallel_workers = 16

-- 日志（压测时关闭详细日志）
log_min_duration_statement = -1      -- 关闭慢查询日志
```

---

## 三、TPC-H 压测

### 3.1 工具选择

```
1. tpch-kit（官方参考实现移植）  — 最严格
2. HammerDB                      — 支持 TPC-H schema
3. pg_tpch                       — PostgreSQL 专用简化工具
```

### 3.2 使用 tpch-kit（推荐）

```bash
# 1. 安装依赖
sudo apt-get install build-essential gcc make

# 2. 获取并编译
git clone https://github.com/ghaerr/tpch-kit.git
cd tpch-kit/dbgen
make -f Makefile.pg    # 使用 PostgreSQL 的 makefile

# 3. 生成数据（-s 指定 scale factor，单位 GB）
./dbgen -s 100
# 生成 8 个 .tbl 文件，总计约 100GB

# 4. 创建表结构
psql -d tpch -f dss/tpch-create-tables.sql

# 5. 批量导入数据（使用 COPY，速度最快）
for tbl in customer lineitem nation orders part partsupp region supplier; do
    echo "Loading ${tbl}..."
    psql -d tpch -c "\\COPY ${tbl} FROM '${tbl}.tbl' WITH (FORMAT csv, DELIMITER '|')"
done

# 6. 创建索引（TPC-H 测试不要求特定索引，可选）
psql -d tpch << 'SQL'
-- 主键/外键索引
ALTER TABLE customer ADD PRIMARY KEY (c_custkey);
ALTER TABLE orders   ADD PRIMARY KEY (o_orderkey);
ALTER TABLE part     ADD PRIMARY KEY (p_partkey);
ALTER TABLE supplier ADD PRIMARY KEY (s_suppkey);
ALTER TABLE nation   ADD PRIMARY KEY (n_nationkey);
ALTER TABLE region   ADD PRIMARY KEY (r_regionkey);
ALTER TABLE partsupp ADD PRIMARY KEY (ps_partkey, ps_suppkey);

-- 常用查询索引
CREATE INDEX idx_lineitem_orderkey ON lineitem (l_orderkey);
CREATE INDEX idx_lineitem_partkey  ON lineitem (l_partkey);
CREATE INDEX idx_lineitem_suppkey  ON lineitem (l_suppkey);
CREATE INDEX idx_orders_custkey    ON orders (o_custkey);
CREATE INDEX idx_partsupp_partkey  ON partsupp (ps_partkey);
CREATE INDEX idx_partsupp_suppkey  ON partsupp (ps_suppkey);
SQL

# 7. 分析统计信息
psql -d tpch -c "ANALYZE;"

# 8. 运行查询（22 条标准查询）
for i in $(seq 1 22); do
    echo "=== Q${i} ==="
    start=$(date +%s%N)
    psql -d tpch -f queries/${i}.sql > /dev/null
    end=$(date +%s%N)
    echo "Q${i}: $(( (end - start) / 1000000 )) ms"
done
```

### 3.3 使用 pg_tpch（轻量方案）

```bash
git clone https://github.com/CitusData/pg_tpch.git
cd pg_tpch

# 修改配置
export DSS_PATH=/data/tpch     # 数据文件路径
export DSS_CONFIG=$(pwd)/tpch-kit/dbgen
export DSS_QUERY=$(pwd)/tpch-kit/dbgen/queries

# 生成数据
make -f Makefile.tpch gen SCALE=10    # SF=10, 约10GB

# 加载
make -f Makefile.tpch load

# 运行
make -f Makefile.tpch run
```

### 3.4 TPC-H 关键 PostgreSQL 调优参数

```sql
-- 与 OLTP 不同，OLAP 需要关注大查询的内存和并行

-- 大幅增加排序和哈希内存
work_mem = '1GB'                     -- TPC-H 的 GROUP BY 和排序非常多
hash_mem_multiplier = 2.0            -- PG 13+，哈希操作可用 2x work_mem

-- 并行查询（OLAP 核心）
max_parallel_workers_per_gather = 8
max_parallel_workers = 16
parallel_tuple_cost = 0.01           -- 降低并行阈值
parallel_setup_cost = 100
min_parallel_table_scan_size = '8MB'
max_parallel_maintenance_workers = 4

-- JIT 编译（PG 11+）
jit = on
jit_above_cost = 100000
jit_inline_above_cost = 500000
jit_optimize_above_cost = 500000

-- 优化器参数
enable_hashjoin = on
enable_mergejoin = on
enable_nestloop = off                -- 强制避免嵌套循环（激进）
random_page_cost = 1.1
effective_io_concurrency = 200
default_statistics_target = 500      -- 更精确的统计信息

-- 记得执行
ANALYZE;
```

### 3.5 TPC-H 22 条查询概览

```
查询分类                  查询编号         核心特征
───────────────────────────────────────────────────────
多表 JOIN 聚合           Q1, Q5, Q9      5-8 表连接，GROUP BY
子查询 (EXISTS/IN)       Q4, Q11, Q16    相关子查询、半连接
时间范围过滤             Q1, Q3, Q5      日期区间 + 聚合
字符串模糊匹配           Q13, Q22        LIKE、正则
排名分析                 Q2, Q3, Q10, Q18  ORDER BY + LIMIT / 窗口函数
分组统计                 Q1, Q6, Q7, Q8  多维分组聚合
高基数 GROUP BY          Q9, Q13, Q18    大量分组
```

---

## 四、结果采集与监控

### 4.1 压测期间监控

```bash
# 系统级监控
iostat -xz 1                  # 磁盘 IO
vmstat 1                      # CPU/内存/IO
pidstat -p $(pgrep postgres) 1  # 进程级 CPU

# PostgreSQL 内置统计
psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
psql -c "SELECT * FROM pg_stat_bgwriter;"
psql -c "SELECT * FROM pg_stat_database WHERE datname = 'tpch';"
```

### 4.2 自动化结果记录脚本

```bash
#!/bin/bash
# collect_stats.sh - 压测期间每10秒采集一次

DB="tpch"
LOG="stats_$(date +%Y%m%d_%H%M%S).csv"

echo "timestamp,active_queries,blocks_hit,blocks_read,tup_returned,tup_fetched" > $LOG

while true; do
    psql -d $DB -t -A -F',' -c "
        SELECT now(),
               (SELECT count(*) FROM pg_stat_activity WHERE state='active'),
               blks_hit, blks_read, tup_returned, tup_fetched
        FROM pg_stat_database WHERE datname='$DB';
    " >> $LOG
    sleep 10
done
```

### 4.3 EXPLAIN ANALYZE 技巧（TPC-H 查询优化必备）

```sql
-- 查看实际执行计划
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) <query>;

-- 关注要点：
-- 1. Seq Scan vs Index Scan 是否合理
-- 2. Hash Join 的 build/probe 选择
-- 3. 并行计划是否生效（Gather / Parallel）
-- 4. 实际行数 vs 预估行数的偏差
-- 5. 排序是否使用了磁盘（Sort Method: external merge）

-- 收集详细统计
EXPLAIN (ANALYZE, BUFFERS, TIMING, SUMMARY, FORMAT JSON) <query>;
```

---

## 五、最佳实践总结

```
┌─────────────────────────────────────────────────────────┐
│                    TPC-C 压测要点                        │
├─────────────────────────────────────────────────────────┤
│ 1. 仓库数（scale）至少 100 以上才能产生争用              │
│ 2. 终端数（并发）逐步加压：8 → 32 → 64 → 128 → 256     │
│ 3. 先暖机再计时（rampup 2-5 分钟）                      │
│ 4. 监控锁争用和死锁（pg_stat_database.deadlocks）       │
│ 5. 关注 checkpoint 写入尖峰（pg_stat_bgwriter）         │
│ 6. synchronous_commit=off 不代表真实生产性能             │
│ 7. 关注 99th percentile 延迟，不仅看吞吐                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    TPC-H 压测要点                        │
├─────────────────────────────────────────────────────────┤
│ 1. Scale Factor ≥ 10 才能体现 OLAP 特性                 │
│ 2. 每条查询至少跑 3 次取中位数（冷启动 vs 热缓存分开记） │
│ 3. 更新统计信息目标：default_statistics_target = 500     │
│ 4. 检查并行执行是否生效（max_parallel_workers）          │
│ 5. 监控 work_mem 是否导致磁盘排序                       │
│ 6. 关注 Q9、Q18 等高基数 GROUP BY 的内存表现            │
│ 7. TPC-H 不建索引也能跑，加索引后对比效果               │
└─────────────────────────────────────────────────────────┘
```

---

## 六、Quick Start 一键脚本

如果你想快速跑完一轮完整的对比，可以把下面的脚本保存为 `run_benchmark.sh`：

```bash
#!/bin/bash
set -e

DB_NAME="benchmark"
PGUSER="postgres"
SF=10          # TPC-H scale factor
WAREHOUSES=10  # TPC-C warehouses

echo "========================================="
echo " PostgreSQL Benchmark Suite"
echo " $(date)"
echo "========================================="

# ===== TPC-C =====
echo ""
echo ">>> [1/2] TPC-C (pgbench, ${WAREHOUSES} warehouses)"
createdb ${DB_NAME} 2>/dev/null || true
pgbench -i -s ${WAREHOUSES} -h localhost -U ${PGUSER} ${DB_NAME}

echo "--- Warmup (60s) ---"
pgbench -c 8 -j 4 -T 60 -h localhost -U ${PGUSER} ${DB_NAME}

echo "--- Test (300s) ---"
for C in 8 32 64 128; do
    echo "--- Concurrency: ${C} ---"
    pgbench -c ${C} -j 4 -T 300 -P 30 -r \
        -h localhost -U ${PGUSER} ${DB_NAME} \
        2>&1 | tee "tpcc_c${C}.log"
done

# ===== TPC-H =====
echo ""
echo ">>> [2/2] TPC-H (SF=${SF})"
# 需要先按上面步骤准备好 TPC-H 数据
for Q in $(seq 1 22); do
    for RUN in 1 2 3; do
        START=$(date +%s%N)
        psql -h localhost -U ${PGUSER} -d tpch \
            -f queries/${Q}.sql > /dev/null 2>&1
        END=$(date +%s%N)
        MS=$(( (END - START) / 1000000 ))
        echo "Q${Q} run${RUN}: ${MS} ms" | tee -a tpch_results.log
    done
done

echo ""
echo ">>> Done! Results saved to tpcc_c*.log and tpch_results.log"
```

---

如果你有具体的 PostgreSQL 版本、硬件配置或测试目标，可以告诉我，我可以进一步帮你定制参数配置和分析策略。
