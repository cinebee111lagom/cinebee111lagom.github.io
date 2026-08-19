---
title: Percona XtraBackup 物理备份与恢复
date: 2026-09-08 03:15:00
tags:
  - MySQL
  - XtraBackup
  - 备份恢复
  - DBA
categories:
  - MySQL
---

## 一、核心原理

Percona XtraBackup 是一款**开源的物理热备份工具**，支持对 InnoDB/XtraDB 存储引擎进行**不锁表**的在线备份。

```
┌─────────────────────────────────────────────────────┐
│                   XtraBackup 工作流程                 │
│                                                     │
│  ① 拷贝 InnoDB 数据页（ibd 文件）                     │
│         ↓                                           │
│  ② 同时持续监控 Redo Log（ib_logfile）                │
│         ↓                                           │
│  ③ 数据页拷贝完毕后，加轻量锁拷贝 .frm / DDL 等元数据   │
│         ↓                                           │
│  ④ Prepare 阶段：应用 Redo Log → 数据一致性点          │
│         ↓                                           │
│  ⑤ Prepare 阶段：回滚未提交事务（可选）                 │
└─────────────────────────────────────────────────────┘
```

**关键点：**
- **备份期间**：InnoDB 引擎表不加全局锁，业务零感知
- **Prepare**：将备份的"崩溃恢复状态"推进到一致性状态

---

## 二、环境准备

### 1. 安装（以 CentOS 8 + MySQL 8.0 为例）

```bash
# 安装 Percona 仓库
yum install https://repo.percona.com/yum/percona-release-latest.noarch.rpm

# 启用 xtrabackup 8.0 版本
percona-release enable-only tools release

# 安装（版本需与 MySQL 版本匹配）
yum install percona-xtrabackup-80
```

### 2. 版本对应关系

| MySQL 版本 | XtraBackup 版本 |
|-----------|----------------|
| 5.7        | 2.4            |
| 8.0        | 8.0            |
| 8.4        | 8.4            |

### 3. 权限配置

```sql
-- 创建备份专用账号
CREATE USER 'bkpuser'@'localhost' IDENTIFIED BY 'StrongP@ss!';

-- MySQL 8.0 所需权限
GRANT SELECT, RELOAD, LOCK TABLES, REPLICATION CLIENT, 
      PROCESS, SUPER, CREATE TABLESPACE 
ON *.* TO 'bkpuser'@'localhost';

FLUSH PRIVILEGES;
```

---

## 三、全量备份（Full Backup）

### 1. 执行备份

```bash
xtrabackup --backup \
  --user=bkpuser \
  --password='StrongP@ss!' \
  --host=127.0.0.1 \
  --port=3306 \
  --target-dir=/data/backup/full/20260819 \
  --parallel=4
```

**参数说明：**

| 参数 | 作用 |
|------|------|
| `--backup` | 执行备份操作 |
| `--target-dir` | 备份目标目录 |
| `--parallel=N` | 并行拷贝线程数 |
| `--compress` | 压缩备份（zstd） |
| `--encrypt=AES256` | 加密备份 |
| `--stream=xbstream` | 流式输出（可用于管道传输） |

### 2. Prepare（应用日志，使数据一致）

```bash
xtrabackup --prepare \
  --target-dir=/data/backup/full/20260819
```

> **Prepare 的本质**：相当于一次 InnoDB 崩溃恢复 —— 用备份期间记录的 redo log 将数据页推到一致性点。

### 3. 恢复

```bash
# ① 停止 MySQL
systemctl stop mysqld

# ② 清空或移走原数据目录
mv /var/lib/mysql /var/lib/mysql_bak

# ③ 拷贝备份到数据目录
xtrabackup --copy-back \
  --target-dir=/data/backup/full/20260819 \
  --datadir=/var/lib/mysql

# ④ 修正权限
chown -R mysql:mysql /var/lib/mysql

# ⑤ 启动 MySQL
systemctl start mysqld
```

> 也可以用 `--move-back` 代替 `--copy-back`（移动而非复制，节省空间）。

---

## 四、增量备份（Incremental Backup）

### 1. 原理

```
全量备份 ──→ 增量备份1 ──→ 增量备份2 ──→ ...
  LSN 0        LSN 100      LSN 250

增量备份 = 只拷贝上次备份之后 LSN 变化的数据页
```

### 2. 执行增量备份

```bash
# 第一次全量
xtrabackup --backup \
  --user=bkpuser --password='StrongP@ss!' \
  --target-dir=/data/backup/full

# 基于全量的增量1
xtrabackup --backup \
  --user=bkpuser --password='StrongP@ss!' \
  --target-dir=/data/backup/inc1 \
  --incremental-basedir=/data/backup/full

# 基于增量1的增量2
xtrabackup --backup \
  --user=bkpuser --password='StrongP@ss!' \
  --target-dir=/data/backup/inc2 \
  --incremental-basedir=/data/backup/inc1
```

### 3. 增量恢复（Prepare 顺序很关键）

```bash
# ① 先 Prepare 全量（不回滚未提交事务）
xtrabackup --prepare \
  --apply-log-only \
  --target-dir=/data/backup/full

# ② 合并增量1
xtrabackup --prepare \
  --apply-log-only \
  --target-dir=/data/backup/full \
  --incremental-dir=/data/backup/inc1

# ③ 合并增量2（最后一个增量，去掉 --apply-log-only）
xtrabackup --prepare \
  --target-dir=/data/backup/full \
  --incremental-dir=/data/backup/inc2

# ④ 恢复
systemctl stop mysqld
xtrabackup --copy-back --target-dir=/data/backup/full
chown -R mysql:mysql /var/lib/mysql
systemctl start mysqld
```

> **关键**：除最后一次，前面的 Prepare 都必须加 `--apply-log-only`，否则无法继续合并后续增量。

---

## 五、流式备份 + 远程传输

```bash
# 备份端：流式压缩 → 通过 SSH 传输到远程
xtrabackup --backup \
  --user=bkpuser --password='StrongP@ss!' \
  --stream=xbstream \
  --parallel=4 | \
  ssh root@backup-server "cat > /data/backup/full.xbstream"

# 远程端：解压恢复
cd /data/backup/
xbstream -x < full.xbstream
xtrabackup --decompress --target-dir=/data/backup/
xtrabackup --prepare --target-dir=/data/backup/
```

---

## 六、备份到 OSS/S3（云原生场景）

```bash
# 通过管道直接推送到 S3
xtrabackup --backup \
  --user=bkpuser --password='StrongP@ss!' \
  --stream=xbstream | \
  gzip | \
  aws s3 cp - s3://my-bucket/mysql/full_20260819.xbstream.gz
```

---

## 七、常用运维脚本

### 全量备份脚本示例

```bash
#!/bin/bash
# mysql_full_backup.sh

BACKUP_DIR="/data/backup/full/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="/var/log/xtrabackup_full.log"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "===== Full Backup Start: $(date) =====" >> "$LOG_FILE"

xtrabackup --backup \
  --user=bkpuser \
  --password='StrongP@ss!' \
  --host=127.0.0.1 \
  --target-dir="$BACKUP_DIR" \
  --parallel=4 \
  --compress \
  --compress-threads=4 \
  2>> "$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "Backup SUCCESS: $BACKUP_DIR" >> "$LOG_FILE"
    
    # 清理过期备份
    find /data/backup/full/ -maxdepth 1 -type d -mtime +${KEEP_DAYS} \
      -exec rm -rf {} \;
else
    echo "Backup FAILED!" >> "$LOG_FILE"
fi

echo "===== Full Backup End: $(date) =====" >> "$LOG_FILE"
```

### Crontab 配置

```bash
# 每天凌晨 2 点全量备份
0 2 * * * /opt/scripts/mysql_full_backup.sh

# 每 6 小时增量备份
0 8,14,20 * * * /opt/scripts/mysql_incr_backup.sh
```

---

## 八、备份验证（至关重要）

```bash
# Prepare 本身就是一种校验 —— 如果备份损坏，prepare 会失败

# 额外校验：在测试环境实际恢复一次
docker run -d --name mysql_test \
  -v /data/backup/full:/backup \
  -e MYSQL_ROOT_PASSWORD=test123 \
  mysql:8.0

# 进入容器执行 copy-back 并验证数据完整性
```

---

## 九、故障排查速查

| 问题 | 排查方向 |
|------|---------|
| `log file is different size` | MySQL 版本与 XtraBackup 版本不匹配 |
| `Missing shared memory` | Windows 环境需加 `--shared-memory-base-name` |
| `Waiting for table metadata lock` | 备份期间有 DDL 操作，等待锁释放 |
| `ib_logfile` 报错 | Prepare 后不要重复 prepare（除非用 `--apply-log-only`） |
| 权限错误 | 检查 `backup` 用户权限、`datadir` 目录权限 |

---

## 十、与 mysqldump 的对比

| 维度 | XtraBackup（物理） | mysqldump（逻辑） |
|------|-------------------|-------------------|
| 备份速度 | 快（直接拷贝文件） | 慢（逐行导出 SQL） |
| 恢复速度 | 快（直接拷贝回来） | 慢（逐条执行 SQL） |
| 对业务影响 | 极小 | 大表锁表风险 |
| 备份粒度 | 实例/库/表级别 | 库/表级别 |
| 跨版本恢复 | 不支持 | 支持 |
| 适用场景 | 大数据量、生产环境 | 小数据量、逻辑迁移 |

---

**最佳实践总结**：生产环境建议 **XtraBackup 全量 + 增量** 方案，配合 binlog 做时间点恢复（PITR），并定期在测试环境验证恢复流程。
