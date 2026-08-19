---
title: MGR MySQL Group Replication磁盘扩容指南
date: 2026-09-08 04:45:00
tags:
  - MySQL
  - MGR
  - 磁盘扩容
  - DBA
categories:
  - MySQL
---

## 一、扩容前检查

### 1. 确认当前磁盘状态

```bash
# 查看磁盘使用情况
df -h

# 查看 MySQL 数据目录大小
du -sh /var/lib/mysql

# 查看 MGR 节点状态
mysql -e "SELECT * FROM performance_schema.replication_group_members;"
```

### 2. 确认 MGR 组状态正常

```sql
-- 所有节点应为 ONLINE
SELECT MEMBER_ID, MEMBER_HOST, MEMBER_STATE, MEMBER_ROLE
FROM performance_schema.replication_group_members;

-- 检查是否有延迟或冲突
SELECT * FROM performance_schema.replication_group_member_stats\G
```

> **关键原则**：扩容时保证集群多数派（Majority）节点在线，避免集群降级或脑裂。

---

## 二、常见扩容方案

### 方案一：LVM 逻辑卷扩容（推荐）

适用于底层使用 LVM 管理磁盘的场景。

#### 步骤 1：对 MySQL 节点执行滚动扩容（逐节点）

```
整体思路：逐节点操作，每次只对一个节点进行扩容，
         该节点暂时从集群中降级或处于正常状态即可。
```

#### 步骤 2：扩容单个节点

```bash
# 1. 查看当前逻辑卷
lvdisplay
vgdisplay

# 2. 如果是云盘，先在控制台扩容云盘大小
# 然后在系统内扫描新容量
echo 1 > /sys/class/block/sda/device/rescan   # SCSI 设备
# 或
partprobe /dev/sda

# 3. 扩展分区（以 parted 为例）
parted /dev/sda
(parted) resizepart 3 100%    # 假设扩展第3个分区
(parted) quit

# 4. 扩展物理卷
pvresize /dev/sda3

# 5. 扩展逻辑卷
lvextend -l +100%FREE /dev/mapper/vg_mysql-lv_mysql

# 6. 扩展文件系统
# XFS 文件系统
xfs_growfs /var/lib/mysql
# EXT4 文件系统
resize2fs /dev/mapper/vg_mysql-lv_mysql
```

#### 步骤 3：验证

```bash
df -h /var/lib/mysql
```

---

### 方案二：云盘在线扩容（阿里云/AWS/Azure 等）

#### 阿里云 ECS 示例

```bash
# 1. 控制台扩容云盘（无需重启）

# 2. 系统内扫描磁盘变更
echo 1 > /sys/class/block/vdb/device/rescan

# 3. 安装 growpart（如未安装）
yum install -y cloud-utils-growpart

# 4. 扩展分区
growpart /dev/vdb 1

# 5. 扩展文件系统
# XFS
xfs_growfs /mountpoint
# EXT4
resize2fs /dev/vdb1
```

---

### 方案三：挂载新磁盘 + 迁移数据

当无法原地扩容时（如本地 SSD），需要迁移数据到更大的磁盘。

```bash
# 1. 新磁盘分区和格式化
fdisk /dev/sdb           # 创建分区
mkfs.xfs /dev/sdb1       # 格式化

# 2. 挂载到临时目录
mkdir /mnt/newdisk
mount /dev/sdb1 /mnt/newdisk

# 3. 停止 MySQL（该节点会自动降级为 OFFLINE）
systemctl stop mysqld

# 4. 复制数据（保留权限）
rsync -avz /var/lib/mysql/ /mnt/newdisk/mysql/

# 5. 更新挂载配置 /etc/fstab
# 原条目注释或删除，新增：
/dev/sdb1  /var/lib/mysql  xfs  defaults  0  0

# 6. 挂载
mount /dev/sdb1 /var/lib/mysql

# 7. 确认权限
chown -R mysql:mysql /var/lib/mysql

# 8. 启动 MySQL
systemctl start mysqld

# 9. 验证节点重新加入集群
mysql -e "SELECT MEMBER_STATE FROM performance_schema.replication_group_members WHERE MEMBER_HOST='$(hostname)';"
```

---

## 三、MGR 专项注意事项

### 1. 逐节点滚动操作

```
操作顺序建议：
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Node 1  │───▶│  Node 2  │───▶│  Node 3  │
│  先扩容   │    │  再扩容   │    │  最后扩容 │
└──────────┘    └──────────┘    └──────────┘
```

- 每完成一个节点的扩容，确认其 `MEMBER_STATE = ONLINE` 后再操作下一个
- 3 节点集群中，任何时刻至少 **2 个节点在线** 保证多数派

### 2. 大事务清理

扩容前清理不必要的大表、binlog、中继日志，可显著减少迁移时间：

```sql
-- 查看 binlog 占用
SHOW BINARY LOGS;

-- 清理 3 天前的 binlog
PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 3 DAY);

-- 检查大表
SELECT table_schema, table_name,
       ROUND(data_length/1024/1024, 2) AS data_mb,
       ROUND(index_length/1024/1024, 2) AS index_mb
FROM information_schema.tables
ORDER BY data_length DESC
LIMIT 20;
```

### 3. 恢复节点状态验证脚本

```sql
-- 逐节点执行，确认集群完整
SELECT
  MEMBER_HOST,
  MEMBER_PORT,
  MEMBER_STATE,
  MEMBER_ROLE,
  COUNT_TRANSACTIONS_IN_QUEUE AS tx_in_queue,
  COUNT_TRANSACTIONS_CHECKED AS tx_checked,
  COUNT_TRANSACTIONS_REMOTE_IN_APPLIER_QUEUE AS remote_applier_queue
FROM performance_schema.replication_group_members
JOIN performance_schema.replication_group_member_stats USING(MEMBER_ID);
```

### 4. 磁盘空间监控阈值建议

| 阈值 | 动作 |
|------|------|
| **70%** | 预警，开始规划扩容 |
| **85%** | 紧急扩容，减少非必要写入 |
| **95%** | 危险，可能导致 MGR 复制中断 |

---

## 四、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 扩容后节点无法重新加入集群 | 数据目录权限/路径变更 | `chown mysql:mysql` + 检查 `datadir` 配置 |
| 扩容期间复制报错 | 磁盘写满导致 applier 停止 | 先释放空间，然后 `START GROUP_REPLICATION` |
| 新磁盘挂载后 UUID 冲突 | 复制了整个 mysql 目录（含 `auto.cnf`） | 删除新目录中 `auto.cnf`，重启自动生成新 UUID |
| Group Replication 拒绝启动 | 节点 GTID 集合与组不一致 | 通过 `group_replication_recovery` 通道重新同步 |

---

如果你能告诉我具体的环境信息（操作系统、是否使用 LVM、云厂商、节点数量等），我可以给出更有针对性的扩容步骤。
