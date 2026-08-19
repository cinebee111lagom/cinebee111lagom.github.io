---
title: MySQL 定期全量备份与Binlog增量保留完整方案
date: 2026-09-07 23:45:00
tags:
  - MySQL
  - 备份恢复
  - binlog
  - DBA
categories:
  - MySQL
---

---

## 一、备份架构总览

```
时间轴：
│◄──── 全量备份(周日) ────►│◄── binlog增量 ──►│◄── binlog增量 ──►│◄──── 全量备份(周日) ────►│
│                          │                  │                  │                          │
周日 02:00               周一               周二               周三 02:00               周四
  FULL                   binlog.003         binlog.004           FULL                 binlog.007
┌──────────┐          ┌──────────┐       ┌──────────┐        ┌──────────┐          ┌──────────┐
│ mysqldump│          │mysql-bin │       │mysql-bin │        │ mysqldump│          │mysql-bin │
│ 或       │          │.000003   │       │.000004   │        │ 或       │          │.000007   │
│xtrabackup│          │          │       │          │        │xtrabackup│          │          │
└──────────┘          └──────────┘       └──────────┘        └──────────┘          └──────────┘
```

**核心思路**：

| 层级 | 工具 | 作用 | 频率 |
|------|------|------|------|
| 全量备份 | mysqldump / xtrabackup | 某一时间点的完整数据快照 | 每天/每周 |
| 增量备份 | binlog | 记录两次全量备份之间的所有变更 | 实时连续 |

**恢复时**：全量备份 + 重放该时间点之后的所有 binlog = 恢复到任意时刻

---

## 二、mysqldump 全量备份

### 1. 基本备份命令

```bash
# 备份单个数据库
mysqldump -u root -p \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --flush-logs \
  --master-data=2 \
  mydb > /backup/mydb_full_$(date +%Y%m%d_%H%M%S).sql
```

### 2. 关键参数解析

| 参数 | 说明 |
|------|------|
| `--single-transaction` | InnoDB 热备，不锁表（开启一致性快照） |
| `--routines` | 包含存储过程和函数 |
| `--triggers` | 包含触发器 |
| `--events` | 包含定时事件 |
| `--flush-logs` | 备份前刷新 binlog，生成新的 binlog 文件 |
| `--master-data=2` | 在备份文件中以注释方式记录 binlog 位置 |
| `--all-databases` | 备份所有数据库 |
| `--set-gtid-purged=OFF` | GTID 环境下按需设置 |

### 3. 备份所有数据库

```bash
mysqldump -u root -p \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --flush-logs \
  --master-data=2 \
  --all-databases \
  > /backup/all_db_full_$(date +%Y%m%d_%H%M%S).sql
```

### 4. 备份并压缩

```bash
mysqldump -u root -p \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --flush-logs \
  --master-data=2 \
  --all-databases \
  | gzip > /backup/all_db_full_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 5. 查看备份文件中的 binlog 位置

```bash
# 在备份 SQL 文件中搜索
head -50 /backup/all_db_full_20260819_020000.sql | grep "CHANGE MASTER"
# 输出示例：
# CHANGE MASTER TO MASTER_LOG_FILE='mysql-bin.000008', MASTER_LOG_POS=154;
```

> 这条信息至关重要——它标记了全量备份结束时的 binlog 位置，增量恢复时从这个位置开始重放 binlog。

---

## 三、XtraBackup 全量备份（推荐用于大库）

### 1. 安装

```bash
# CentOS / RHEL
yum install -y percona-xtrabackup-80

# Ubuntu / Debian
apt install -y percona-xtrabackup-80
```

### 2. 全量备份

```bash
xtrabackup --backup \
  --user=root \
  --password='your_password' \
  --target-dir=/backup/full/$(date +%Y%m%d) \
  --parallel=4
```

### 3. 准备（apply-log）备份

```bash
# 恢复前必须执行，将 redo log 应用到备份数据
xtrabackup --prepare --target-dir=/backup/full/20260819
```

### 4. 从 XtraBackup 备份中获取 binlog 位置

```bash
cat /backup/full/20260819/xtrabackup_binlog_info
# 输出示例：
# mysql-bin.000008    154    aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
```

### 5. XtraBackup 增量备份

```bash
# 第一次增量（基于全量）
xtrabackup --backup \
  --user=root \
  --password='your_password' \
  --target-dir=/backup/inc1/$(date +%Y%m%d) \
  --incremental-basedir=/backup/full/20260818 \
  --parallel=4

# 第二次增量（基于上一次增量）
xtrabackup --backup \
  --user=root \
  --password='your_password' \
  --target-dir=/backup/inc2/$(date +%Y%m%d) \
  --incremental-basedir=/backup/inc1/20260819 \
  --parallel=4
```

### 6. XtraBackup 恢复流程

```bash
# 1) 准备全量备份（不回滚未提交事务）
xtrabackup --prepare --apply-log-only --target-dir=/backup/full/20260818

# 2) 合并第一次增量
xtrabackup --prepare --apply-log-only \
  --target-dir=/backup/full/20260818 \
  --incremental-dir=/backup/inc1/20260819

# 3) 合并最后一次增量（不加 --apply-log-only）
xtrabackup --prepare \
  --target-dir=/backup/full/20260818 \
  --incremental-dir=/backup/inc2/20260820

# 4) 恢复数据
systemctl stop mysqld
rm -rf /var/lib/mysql/*
xtrabackup --copy-back --target-dir=/backup/full/20260818
chown -R mysql:mysql /var/lib/mysql
systemctl start mysqld
```

---

## 四、Binlog 增量保留策略

### 1. 确认 binlog 配置

```ini
# my.cnf
[mysqld]
server-id                  = 1
log_bin                    = /var/lib/mysql/mysql-bin
binlog_format              = ROW
binlog_expire_logs_seconds = 604800    # 7天 = 7*24*3600
max_binlog_size            = 512M
sync_binlog                = 1         # 每次提交刷盘，最安全
```

### 2. 查看当前 binlog 状态

```sql
-- 查看所有 binlog 文件
SHOW BINARY LOGS;

-- 查看当前 binlog
SHOW MASTER STATUS;

-- 查看 binlog 过期策略
SHOW VARIABLES LIKE '%expire%';
SHOW VARIABLES LIKE '%binlog%';
```

### 3. 手动管理 binlog

```sql
-- 删除 3 天前的 binlog
PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 3 DAY);

-- 删除指定 binlog 之前的所有文件
PURGE BINARY LOGS TO 'mysql-bin.000010';

-- 重置所有 binlog（危险！慎用）
RESET MASTER;
```

### 4. binlog 存储空间监控

```bash
# 查看 binlog 占用的磁盘空间
du -sh /var/lib/mysql/mysql-bin.*

# 监控脚本
#!/bin/bash
BINLOG_DIR="/var/lib/mysql"
THRESHOLD_GB=50

usage=$(du -sm ${BINLOG_DIR}/mysql-bin.* 2>/dev/null | awk '{sum+=$1} END {print sum/1024}')
if (( $(echo "$usage > $THRESHOLD_GB" | bc -l) )); then
    echo "[WARNING] binlog 磁盘占用 ${usage}GB 超过阈值 ${THRESHOLD_GB}GB" \
      | mail -s "MySQL binlog 空间告警" dba@company.com
fi
```

---

## 五、完整自动化备份脚本

### 1. 全量备份脚本（mysqldump 版）

```bash
#!/bin/bash
# /opt/scripts/mysql_full_backup.sh

# ============ 配置 ============
MYSQL_USER="backup_user"
MYSQL_PASS="secure_password"
BACKUP_DIR="/backup/mysql/full"
RETENTION_DAYS=7          # 全量备份保留天数
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/mysql_backup.log"

# ============ 函数 ============
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

# ============ 创建目录 ============
mkdir -p ${BACKUP_DIR}

# ============ 记录 binlog 位置 ============
log "记录当前 binlog 位置..."
BINLOG_POS=$(mysql -u${MYSQL_USER} -p${MYSQL_PASS} -e "SHOW MASTER STATUS\G" 2>/dev/null)
log "binlog 位置: ${BINLOG_POS}"

# ============ 刷新 binlog ============
log "刷新 binlog（生成新的 binlog 文件）..."
mysql -u${MYSQL_USER} -p${MYSQL_PASS} -e "FLUSH BINARY LOGS;" 2>/dev/null

# ============ 执行全量备份 ============
log "开始全量备份..."
mysqldump -u${MYSQL_USER} -p${MYSQL_PASS} \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --master-data=2 \
  --all-databases \
  --set-gtid-purged=OFF \
  | gzip > ${BACKUP_DIR}/full_backup_${DATE}.sql.gz

# ============ 检查备份结果 ============
if [ $? -eq 0 ]; then
    SIZE=$(du -sh ${BACKUP_DIR}/full_backup_${DATE}.sql.gz | awk '{print $1}')
    log "全量备份成功: full_backup_${DATE}.sql.gz (${SIZE})"
else
    log "ERROR: 全量备份失败！"
    exit 1
fi

# ============ 删除过期备份 ============
log "清理 ${RETENTION_DAYS} 天前的过期备份..."
find ${BACKUP_DIR} -name "full_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
DELETED_COUNT=$(find ${BACKUP_DIR} -name "full_backup_*.sql.gz" -mtime +${RETENTION_DAYS} | wc -l)
log "已清理 ${DELETED_COUNT} 个过期备份文件"

# ============ 备份 binlog ============
log "归档当前 binlog 文件..."
BINLOG_DIR="/var/lib/mysql"
BINLOG_ARCHIVE="/backup/mysql/binlog/${DATE}"
mkdir -p ${BINLOG_ARCHIVE}

# 获取全量备份对应的 binlog 文件列表
FIRST_BINLOG=$(mysql -u${MYSQL_USER} -p${MYSQL_PASS} -e "SHOW BINARY LOGS\G" 2>/dev/null \
  | grep "Log_name" | head -1 | awk '{print $2}')
CURRENT_BINLOG=$(mysql -u${MYSQL_USER} -p${MYSQL_PASS} -e "SHOW MASTER STATUS\G" 2>/dev/null \
  | grep "File" | awk '{print $2}')

# 拷贝 binlog 到归档目录
cp ${BINLOG_DIR}/mysql-bin.* ${BINLOG_ARCHIVE}/ 2>/dev/null
log "binlog 已归档到 ${BINLOG_ARCHIVE}"

# ============ 验证备份完整性 ============
log "验证备份文件完整性..."
gzip -t ${BACKUP_DIR}/full_backup_${DATE}.sql.gz
if [ $? -eq 0 ]; then
    log "备份文件完整性验证通过"
else
    log "ERROR: 备份文件损坏！"
    exit 1
fi

log "========== 全量备份任务完成 =========="
```

### 2. Binlog 定期归档脚本

```bash
#!/bin/bash
# /opt/scripts/mysql_binlog_archive.sh

MYSQL_USER="backup_user"
MYSQL_PASS="secure_password"
BINLOG_DIR="/var/lib/mysql"
ARCHIVE_DIR="/backup/mysql/binlog"
RETENTION_DAYS=14
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/mysql_binlog_archive.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

# ============ 刷新 binlog ============
log "刷新 binlog..."
mysql -u${MYSQL_USER} -p${MYSQL_PASS} -e "FLUSH BINARY LOGS;" 2>/dev/null

# ============ 获取当前所有 binlog ============
BINLOGS=$(mysql -u${MYSQL_USER} -p${MYSQL_PASS} -N -e "SHOW BINARY LOGS;" 2>/dev/null \
  | awk '{print $1}')
CURRENT=$(mysql -u${MYSQL_USER} -p${MYSQL_PASS} -N -e "SHOW MASTER STATUS;" 2>/dev/null \
  | awk '{print $1}')

# ============ 归档旧 binlog（非当前正在使用的） ============
DAILY_ARCHIVE="${ARCHIVE_DIR}/$(date +%Y%m%d)"
mkdir -p ${DAILY_ARCHIVE}

for logfile in ${BINLOGS}; do
    if [ "${logfile}" != "${CURRENT}" ]; then
        if [ ! -f "${DAILY_ARCHIVE}/${logfile}" ]; then
            cp ${BINLOG_DIR}/${logfile} ${DAILY_ARCHIVE}/
            log "归档 binlog: ${logfile}"
        fi
    fi
done

# ============ 清理过期归档 ============
find ${ARCHIVE_DIR} -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null
log "清理 ${RETENTION_DAYS} 天前的过期 binlog 归档"

# ============ 监控 binlog 磁盘占用 ============
BINLOG_SIZE=$(du -sm ${BINLOG_DIR}/mysql-bin.* 2>/dev/null | awk '{sum+=$1} END {print sum}')
log "当前 binlog 磁盘占用: ${BINLOG_SIZE}MB"

MAX_SIZE=10240  # 10GB 告警阈值
if [ "${BINLOG_SIZE}" -gt "${MAX_SIZE}" ]; then
    log "WARNING: binlog 磁盘占用 ${BINLOG_SIZE}MB 超过阈值 ${MAX_SIZE}MB！"
fi

log "========== binlog 归档任务完成 =========="
```

### 3. Crontab 定时任务配置

```bash
# 编辑 crontab
crontab -e
```

```cron
# 每天凌晨 2 点执行全量备份
0 2 * * * /opt/scripts/mysql_full_backup.sh >> /var/log/mysql_backup.log 2>&1

# 每 4 小时归档一次 binlog
0 */4 * * * /opt/scripts/mysql_binlog_archive.sh >> /var/log/mysql_binlog_archive.log 2>&1

# 每天凌晨 4 点检查备份完整性
0 4 * * * /opt/scripts/mysql_backup_verify.sh >> /var/log/mysql_backup_verify.log 2>&1
```

---

## 六、mysqldump 恢复全流程

### 场景：恢复到 2026-08-19 10:30:00（误操作前）

```bash
# ============ 步骤 1：确认最近的全量备份 ============
ls -lh /backup/mysql/full/
# full_backup_20260818_020000.sql.gz  ← 最近一次全量备份(8月18日凌晨)

# ============ 步骤 2：确认备份文件中的 binlog 起始位置 ============
zcat /backup/mysql/full/full_backup_20260818_020000.sql.gz \
  | head -80 | grep "CHANGE MASTER"
# CHANGE MASTER TO MASTER_LOG_FILE='mysql-bin.000008', MASTER_LOG_POS=154;
# 起始位置：mysql-bin.000008 @ 154

# ============ 步骤 3：找到误操作所在的 binlog 位置 ============
# 在归档的 binlog 中查找
mysqlbinlog \
  --start-datetime="2026-08-19 10:25:00" \
  --stop-datetime="2026-08-19 10:35:00" \
  -v --base64-output=DECODE-ROWS \
  /backup/mysql/binlog/20260819/mysql-bin.000009 \
  | grep -B5 "DELETE.*orders"
# 找到误操作的 position：起始 7856，结束 8130

# ============ 步骤 4：创建临时恢复库 ============
mysql -u root -p -e "CREATE DATABASE recover_temp;"

# ============ 步骤 5：恢复全量备份到临时库 ============
zcat /backup/mysql/full/full_backup_20260818_020000.sql.gz \
  | mysql -u root -p recover_temp

# ============ 步骤 6：重放 binlog（从备份点到误操作之前） ============
mysqlbinlog \
  --start-position=154 \
  --stop-position=7856 \
  /backup/mysql/binlog/20260818/mysql-bin.000008 \
  /backup/mysql/binlog/20260819/mysql-bin.000009 \
  | mysql -u root -p recover_temp

# ============ 步骤 7：验证恢复数据 ============
mysql -u root -p -e "
  SELECT COUNT(*) AS recoverd_rows FROM recover_temp.orders WHERE status='pending';
"

# ============ 步骤 8：将恢复的数据导回生产库 ============
mysql -u root -p -e "
  INSERT INTO production.orders
  SELECT * FROM recover_temp.orders
  WHERE status='pending'
  AND order_id NOT IN (SELECT order_id FROM production.orders);
"

# ============ 步骤 9：清理临时库 ============
mysql -u root -p -e "DROP DATABASE recover_temp;"
```

---

## 七、XtraBackup 恢复全流程

```bash
# ============ 步骤 1：停止 MySQL ============
systemctl stop mysqld

# ============ 步骤 2：备份当前数据（以防万一） ============
mv /var/lib/mysql /var/lib/mysql_broken_backup

# ============ 步骤 3：准备全量备份 ============
xtrabackup --prepare --apply-log-only \
  --target-dir=/backup/mysql/full/20260818

# ============ 步骤 4：合并增量备份（如果有） ============
xtrabackup --prepare --apply-log-only \
  --target-dir=/backup/mysql/full/20260818 \
  --incremental-dir=/backup/mysql/inc/20260819

# 最后一次合并不加 --apply-log-only
xtrabackup --prepare \
  --target-dir=/backup/mysql/full/20260818

# ============ 步骤 5：恢复数据文件 ============
xtrabackup --copy-back --target-dir=/backup/mysql/full/20260818

# ============ 步骤 6：修改权限 ============
chown -R mysql:mysql /var/lib/mysql

# ============ 步骤 7：启动 MySQL ============
systemctl start mysqld

# ============ 步骤 8：重放 binlog 到指定时间点 ============
mysqlbinlog \
  --start-datetime="2026-08-18 02:00:00" \
  --stop-datetime="2026-08-19 10:30:00" \
  /var/lib/mysql/mysql-bin.000008 \
  /var/lib/mysql/mysql-bin.000009 \
  | mysql -u root -p
```

---

## 八、mysqldump vs XtraBackup 对比

| 对比项 | mysqldump | XtraBackup |
|--------|-----------|------------|
| **备份方式** | 逻辑备份（导出 SQL） | 物理备份（拷贝数据文件） |
| **备份速度** | 慢（大库耗时长） | 快（直接拷贝文件） |
| **恢复速度** | 慢（需重放 SQL） | 快（直接替换文件） |
| **是否锁表** | InnoDB 不锁（--single-transaction） | 不锁表 |
| **压缩** | 需配合 gzip | 支持原生压缩 |
| **增量备份** | 不支持（需配合 binlog） | 支持（基于 LSN） |
| **跨版本恢复** | 支持 | 有限制 |
| **适用库大小** | < 100GB | 任意大小 |
| **安装** | MySQL 自带 | 需额外安装 |
| **可读性** | SQL 文本可直接查看 | 二进制文件不可直接阅读 |

**选型建议**：

```
数据库 < 50GB   ──→  mysqldump 够用，简单方便
数据库 50~500GB ──→  XtraBackup，备份恢复效率高
数据库 > 500GB  ──→  XtraBackup + 压缩 + 并行
```

---

## 九、备份策略最佳实践

### 1. 推荐备份策略

```
┌─────────────────────────────────────────────────────┐
│                  备 策 推 荐                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  小型数据库 (< 50GB)                                 │
│  ├── 每天 02:00 mysqldump 全量备份                   │
│  ├── binlog 持续写入，保留 7~14 天                    │
│  └── 每周验证备份可恢复性                             │
│                                                     │
│  中型数据库 (50~500GB)                                │
│  ├── 每天 02:00 XtraBackup 全量备份                  │
│  ├── 每 4~6 小时 XtraBackup 增量备份                 │
│  ├── binlog 持续写入，保留 7~14 天                    │
│  └── 每周验证备份可恢复性                             │
│                                                     │
│  大型数据库 (> 500GB)                                 │
│  ├── 每周日 XtraBackup 全量备份                      │
│  ├── 每天 XtraBackup 增量备份                        │
│  ├── binlog 持续写入，保留 14~30 天                   │
│  ├── binlog 实时归档到远端存储                        │
│  └── 定期演练恢复流程                                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 2. 3-2-1 备份原则

```
3 份数据副本：1 份生产数据 + 2 份备份
2 种存储介质：本地磁盘 + 远程存储/NAS/OSS
1 份异地备份：至少 1 份备份存放在异地/云端
```

```bash
# 示例：备份同步到远程服务器
rsync -avz --progress \
  /backup/mysql/ \
  backup-server:/remote-backup/mysql/

# 或上传到对象存储
aws s3 sync /backup/mysql/ s3://my-mysql-backup/ --storage-class STANDARD_IA
```

### 3. 备份验证脚本

```bash
#!/bin/bash
# /opt/scripts/mysql_backup_verify.sh

BACKUP_FILE="/backup/mysql/full/full_backup_$(date +%Y%m%d)*.sql.gz"
VERIFY_DB="verify_test_$(date +%s)"
LOG_FILE="/var/log/mysql_backup_verify.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a ${LOG_FILE}
}

log "========== 开始备份验证 =========="

# 1) 检查备份文件是否存在
LATEST_BACKUP=$(ls -t ${BACKUP_FILE} 2>/dev/null | head -1)
if [ -z "${LATEST_BACKUP}" ]; then
    log "ERROR: 未找到今日备份文件！"
    exit 1
fi

# 2) 检查文件完整性
gzip -t ${LATEST_BACKUP}
if [ $? -ne 0 ]; then
    log "ERROR: 备份文件损坏: ${LATEST_BACKUP}"
    exit 1
fi

# 3) 尝试恢复到临时库
log "创建临时验证库: ${VERIFY_DB}"
mysql -u root -p -e "CREATE DATABASE ${VERIFY_DB};" 2>/dev/null

log "开始恢复验证..."
zcat ${LATEST_BACKUP} | mysql -u root -p ${VERIFY_DB} 2>/dev/null
if [ $? -ne 0 ]; then
    log "ERROR: 备份恢复失败！"
    mysql -u root -p -e "DROP DATABASE ${VERIFY_DB};" 2>/dev/null
    exit 1
fi

# 4) 检查表完整性
TABLE_COUNT=$(mysql -u root -p -N -e \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${VERIFY_DB}';" 2>/dev/null)
log "恢复表数量: ${TABLE_COUNT}"

# 5) 清理
mysql -u root -p -e "DROP DATABASE ${VERIFY_DB};" 2>/dev/null
log "验证库已清理"

log "========== 备份验证通过 =========="
```

---

## 十、监控与告警

### 1. 备份监控检查清单

```bash
#!/bin/bash
# 每日备份巡检脚本

echo "===== MySQL 备份巡检报告 $(date) ====="

# 1) 最近一次备份是否成功
echo -e "\n--- 最近备份 ---"
ls -lhrt /backup/mysql/full/ | tail -3

# 2) binlog 是否正常写入
echo -e "\n--- 当前 binlog ---"
mysql -uroot -p -e "SHOW MASTER STATUS;" 2>/dev/null

# 3) binlog 磁盘占用
echo -e "\n--- binlog 磁盘占用 ---"
du -sh /var/lib/mysql/mysql-bin.* 2>/dev/null

# 4) 备份目录磁盘占用
echo -e "\n--- 备份目录磁盘占用 ---"
du -sh /backup/mysql/

# 5) 备份保留数量
echo -e "\n--- 备份文件统计 ---"
echo "全量备份: $(find /backup/mysql/full -name '*.sql.gz' | wc -l) 个"
echo "binlog归档: $(find /backup/mysql/binlog -type d -maxdepth 1 | wc -l) 天"
```

### 2. 关键告警项

| 告警场景 | 告警级别 | 触发条件 |
|---------|---------|---------|
| 备份任务失败 | 严重 | 任意一次备份脚本退出码非 0 |
| 备份文件损坏 | 严重 | gzip -t 校验失败 |
| binlog 未写入 | 严重 | binlog 文件长时间未更新 |
| binlog 磁盘超限 | 警告 | binlog 占用 > 50GB |
| 备份目录磁盘不足 | 警告 | 剩余空间 < 20% |
| binlog 过期未归档 | 警告 | binlog 已清理但未归档 |
| 未按时备份 | 警告 | 超过 36 小时未执行全量备份 |

---

## 十一、总结

```
完整的数据保护体系 = 全量备份 + binlog 增量 + 异地存储 + 定期验证
     │                    │            │              │            │
     │                    │            │              │            │
     ▼                    ▼            ▼              ▼            ▼
  策略规划          mysqldump /     binlog 持续     3-2-1 原则    每周恢复
                   XtraBackup       保留 7~30天     远程同步      演练
```

**核心要点**：

1. **全量备份**是基础 —— 决定恢复的起点
2. **binlog 是灵魂** —— 决定恢复的精度（可精确到秒级）
3. **定期验证**是保障 —— 没验证过的备份等于没有备份
4. **异地存储**是底线 —— 本地灾难时的最后防线
5. **自动化**是关键 —— 人工操作不可靠，脚本化 + 定时任务 + 监控告警
