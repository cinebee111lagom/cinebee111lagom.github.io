---
title: MySQL Binlog DML 统计分析
date: 2026-09-08 07:15:00
tags:
  - MySQL
  - binlog
  - DML
  - DBA
categories:
  - MySQL
---

## 一、使用 mysqlbinlog 原生命令行

### 1. 基础：按类型统计 DML 事件数量

```bash
# 解析 binlog 并统计各 DML 类型
mysqlbinlog --no-defaults --base64-output=decode-rows -v \
  /var/lib/mysql/binlog.000123 | \
  grep -c "^### INSERT INTO"

mysqlbinlog --no-defaults --base64-output=decode-rows -v \
  /var/lib/mysql/binlog.000123 | \
  grep -c "^### UPDATE"

mysqlbinlog --no-defaults --base64-output=decode-rows -v \
  /var/lib/mysql/binlog.000123 | \
  grep -c "^### DELETE FROM"
```

### 2. 按表维度统计

```bash
mysqlbinlog --no-defaults --base64-output=decode-rows -v \
  /var/lib/mysql/binlog.000123 | \
  grep "^###" | grep -E "(INSERT INTO|UPDATE|DELETE FROM)" | \
  sed 's/### //' | sort | uniq -c | sort -rn
```

输出示例：
```
   1523 INSERT INTO `mydb`.`orders`
    876 UPDATE `mydb`.`users`
    432 DELETE FROM `mydb`.`logs`
     98 INSERT INTO `mydb`.`audit`
```

### 3. 按时间段统计

```bash
mysqlbinlog --no-defaults --base64-output=decode-rows -v \
  --start-datetime="2026-08-19 00:00:00" \
  --stop-datetime="2026-08-19 23:59:59" \
  /var/lib/mysql/binlog.000123 | \
  grep -c "^### INSERT INTO"
```

---

## 二、Shell 脚本：完整统计报表

```bash
#!/bin/bash
# analyze_binlog_dml.sh - Binlog DML 统计分析
# 用法: ./analyze_binlog_dml.sh <binlog文件或路径> [start-time] [stop-time]

BINLOG_PATH="${1:?用法: $0 <binlog文件> [start-time] [stop-time]}"
START_TIME="${2:-}"
STOP_TIME="${3:-}"

# 构建时间过滤参数
TIME_OPTS=""
[[ -n "$START_TIME" ]] && TIME_OPTS="$TIME_OPTS --start-datetime=$START_TIME"
[[ -n "$STOP_TIME"  ]] && TIME_OPTS="$TIME_OPTS --stop-datetime=$STOP_TIME"

echo "========================================"
echo "  Binlog DML 统计分析报告"
echo "  文件: $BINLOG_PATH"
echo "  时间: ${START_TIME:-全部} ~ ${STOP_TIME:-全部}"
echo "  生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 解析 binlog（只需一次 IO，结果存临时文件）
TMPFILE=$(mktemp)
mysqlbinlog --no-defaults --base64-output=decode-rows -v \
  $TIME_OPTS "$BINLOG_PATH" > "$TMPFILE" 2>/dev/null

echo ""
echo ">>> 总览"
echo "----------------------------------------"
total_insert=$(grep -c "^### INSERT INTO" "$TMPFILE")
total_update=$(grep -c "^### UPDATE" "$TMPFILE")
total_delete=$(grep -c "^### DELETE FROM" "$TMPFILE")
total=$((total_insert + total_update + total_delete))

printf "  INSERT : %10d  (%6.2f%%)\n" "$total_insert" \
  "$(echo "scale=2; $total_insert*100/($total+0.01)" | bc)"
printf "  UPDATE : %10d  (%6.2f%%)\n" "$total_update" \
  "$(echo "scale=2; $total_update*100/($total+0.01)" | bc)"
printf "  DELETE : %10d  (%6.2f%%)\n" "$total_delete" \
  "$(echo "scale=2; $total_delete*100/($total+0.01)" | bc)"
printf "  -------  ----------\n"
printf "  TOTAL  : %10d\n" "$total"

echo ""
echo ">>> 按库.表维度统计 (Top 20)"
echo "----------------------------------------"
grep -E "^### (INSERT INTO|UPDATE|DELETE FROM)" "$TMPFILE" | \
  sed -E 's/### (INSERT INTO|UPDATE|DELETE FROM) //' | \
  sed 's/ SET.*//' | sed 's/ WHERE.*//' | \
  sort | uniq -c | sort -rn | head -20

echo ""
echo ">>> DML 类型分布 (按表)"
echo "----------------------------------------"
{
  grep "^### INSERT INTO" "$TMPFILE" | \
    sed 's/### INSERT INTO /INSERT /' | \
    sed 's/ SET.*//' | sed 's/ .*//' | sort | uniq -c | \
    awk '{printf "  %-60s INSERT: %d\n", $2, $1}'

  grep "^### UPDATE" "$TMPFILE" | \
    sed 's/### UPDATE //' | \
    sed 's/ SET.*//' | sed 's/ .*//' | sort | uniq -c | \
    awk '{printf "  %-60s UPDATE: %d\n", $2, $1}'

  grep "^### DELETE FROM" "$TMPFILE" | \
    sed 's/### DELETE FROM /DELETE /' | \
    sed 's/ WHERE.*//' | sed 's/ .*//' | sort | uniq -c | \
    awk '{printf "  %-60s DELETE: %d\n", $2, $1}'
} | sort

# 清理
rm -f "$TMPFILE"

echo ""
echo "========================================"
echo "  分析完成"
echo "========================================"
```

---

## 三、Python 脚本：更精细的分析

```python
#!/usr/bin/env python3
"""
binlog_dml_stats.py
Binlog DML 统计分析工具 - 支持多文件 / 时间分段 / CSV 导出
用法:
  python3 binlog_dml_stats.py /var/lib/mysql/binlog.000123
  python3 binlog_dml_stats.py /var/lib/mysql/binlog.*  --output report.csv
  python3 binlog_dml_stats.py /var/lib/mysql/binlog.000123 --start "2026-08-19 08:00" --stop "2026-08-19 12:00"
"""

import subprocess
import re
import sys
import csv
import argparse
from collections import defaultdict
from datetime import datetime


def parse_binlog(binlog_file: str, start_time: str = None, stop_time: str = None):
    """解析单个 binlog 文件，返回结构化 DML 记录"""
    cmd = [
        "mysqlbinlog", "--no-defaults",
        "--base64-output=decode-rows", "-v",
    ]
    if start_time:
        cmd += [f"--start-datetime={start_time}"]
    if stop_time:
        cmd += [f"--stop-datetime={stop_time}"]
    cmd.append(binlog_file)

    result = subprocess.run(cmd, capture_output=True, text=True)

    # 解析时间戳
    ts_pattern = re.compile(r"^#(\d{6}\s+\d{2}:\d{2}:\d{2})")
    # 解析 DML 语句
    dml_pattern = re.compile(
        r"^### (INSERT INTO|UPDATE|DELETE FROM) (`[^`]+`\.`[^`]+`|`\w+`)"
    )
    # 完整表名提取
    table_pattern = re.compile(r"`(\w+)`\.`(\w+)`|`(\w+)`")

    current_ts = None
    records = []

    for line in result.stdout.splitlines():
        # 时间戳行
        ts_match = ts_pattern.match(line)
        if ts_match:
            raw = ts_match.group(1)
            # binlog 格式: YYMMDD HH:MM:SS -> 补全年份
            try:
                current_ts = datetime.strptime(f"20{raw}", "%Y%m%d %H:%M:%S")
            except ValueError:
                current_ts = None
            continue

        # DML 行
        dml_match = dml_pattern.match(line)
        if dml_match:
            op = dml_match.group(1).split()[0]  # INSERT / UPDATE / DELETE
            table_raw = dml_match.group(2)

            # 提取 db 和 table
            full_match = re.search(r"`(\w+)`\.`(\w+)`", table_raw)
            if full_match:
                db, tb = full_match.group(1), full_match.group(2)
            else:
                single = re.search(r"`(\w+)`", table_raw)
                db, tb = "(unknown)", single.group(1) if single else "(unknown)"

            records.append({
                "timestamp": current_ts,
                "operation": op,
                "database": db,
                "table": tb,
                "full_table": f"{db}.{tb}",
            })

    return records


def build_statistics(records):
    """生成多维度统计"""
    stats = {
        "total": len(records),
        "by_op": defaultdict(int),               # INSERT/UPDATE/DELETE
        "by_table": defaultdict(int),             # db.table -> count
        "by_table_op": defaultdict(lambda: defaultdict(int)),  # db.table -> {op: count}
        "by_db": defaultdict(int),                # db -> count
        "by_hour": defaultdict(int),              # "HH:00" -> count
    }

    for r in records:
        stats["by_op"][r["operation"]] += 1
        stats["by_table"][r["full_table"]] += 1
        stats["by_table_op"][r["full_table"]][r["operation"]] += 1
        stats["by_db"][r["database"]] += 1
        if r["timestamp"]:
            hour_key = r["timestamp"].strftime("%Y-%m-%d %H:00")
            stats["by_hour"][hour_key] += 1

    return stats


def print_report(stats, filename):
    """打印格式化报告"""
    total = stats["total"]
    if total == 0:
        print(f"\n[{filename}] 无 DML 事件\n")
        return

    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  Binlog DML 统计 - {filename}")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(sep)

    # --- 总览 ---
    print(f"\n{'─'*40}")
    print(f"  总 DML 事件: {total:,}")
    print(f"{'─'*40}")
    for op in ("INSERT", "UPDATE", "DELETE"):
        cnt = stats["by_op"].get(op, 0)
        pct = cnt / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        print(f"  {op:<8} {cnt:>10,}  ({pct:6.2f}%)  {bar}")

    # --- 按库统计 ---
    print(f"\n{'─'*40}")
    print("  按数据库统计")
    print(f"{'─'*40}")
    for db, cnt in sorted(stats["by_db"].items(), key=lambda x: -x[1]):
        print(f"  {db:<30} {cnt:>10,}")

    # --- 按表统计 (Top 30) ---
    print(f"\n{'─'*40}")
    print("  按表统计 (Top 30)")
    print(f"{'─'*40}")
    print(f"  {'表名':<45} {'INSERT':>8} {'UPDATE':>8} {'DELETE':>8} {'合计':>8}")
    print(f"  {'─'*45} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    sorted_tables = sorted(stats["by_table"].items(), key=lambda x: -x[1])[:30]
    for table, _ in sorted_tables:
        ops = stats["by_table_op"][table]
        ins = ops.get("INSERT", 0)
        upd = ops.get("UPDATE", 0)
        dlt = ops.get("DELETE", 0)
        tot = ins + upd + dlt
        print(f"  {table:<45} {ins:>8,} {upd:>8,} {dlt:>8,} {tot:>8,}")

    # --- 按小时统计 ---
    if stats["by_hour"]:
        print(f"\n{'─'*40}")
        print("  按小时分布")
        print(f"{'─'*40}")
        max_cnt = max(stats["by_hour"].values()) if stats["by_hour"] else 1
        for hour, cnt in sorted(stats["by_hour"].items()):
            bar_len = int(cnt / max_cnt * 40)
            bar = "▓" * bar_len
            print(f"  {hour}  {cnt:>8,}  {bar}")

    print(f"\n{sep}\n")


def export_csv(stats, output_path):
    """导出 CSV"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["表名", "INSERT", "UPDATE", "DELETE", "合计"])
        for table, _ in sorted(stats["by_table"].items(), key=lambda x: -x[1]):
            ops = stats["by_table_op"][table]
            ins = ops.get("INSERT", 0)
            upd = ops.get("UPDATE", 0)
            dlt = ops.get("DELETE", 0)
            writer.writerow([table, ins, upd, dlt, ins + upd + dlt])
    print(f"CSV 已导出: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Binlog DML 统计分析工具")
    parser.add_argument("binlogs", nargs="+", help="binlog 文件路径（支持多个）")
    parser.add_argument("--start", help="起始时间 (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--stop", help="结束时间 (YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--output", "-o", help="导出 CSV 文件路径")
    args = parser.parse_args()

    all_records = []
    for bf in args.binlogs:
        print(f"正在解析: {bf} ...")
        records = parse_binlog(bf, args.start, args.stop)
        all_records.extend(records)
        print(f"  -> 发现 {len(records):,} 条 DML 事件")

    if not all_records:
        print("\n未发现任何 DML 事件，请检查文件路径和时间范围。")
        sys.exit(0)

    # 合并统计
    stats = build_statistics(all_records)
    print_report(stats, f"{len(args.binlogs)} 个文件")

    # CSV 导出
    if args.output:
        export_csv(stats, args.output)


if __name__ == "__main__":
    main()
```

---

## 四、按时间分段统计（发现热点时段）

```bash
#!/bin/bash
# hourly_dml_stats.sh - 按小时分段统计 DML
BINLOG="$1"

mysqlbinlog --no-defaults --base64-output=decode-rows -v "$BINLOG" | \
awk '
  /^#[0-9]{6}[[:space:]]+[0-9]{2}:/ {
    split($2, t, ":")
    hour = t[1]
  }
  /^### INSERT INTO/  { count[hour]["INSERT"]++; count[hour]["TOTAL"]++ }
  /^### UPDATE/       { count[hour]["UPDATE"]++;  count[hour]["TOTAL"]++ }
  /^### DELETE FROM/  { count[hour]["DELETE"]++;  count[hour]["TOTAL"]++ }
  END {
    printf "%-6s %10s %10s %10s %10s\n", "Hour", "INSERT", "UPDATE", "DELETE", "TOTAL"
    printf "%-6s %10s %10s %10s %10s\n", "------", "----------", "----------", "----------", "----------"
    for (h in count) {
      printf "%-6s %10d %10d %10d %10d\n", 
        h, 
        count[h]["INSERT"]+0, 
        count[h]["UPDATE"]+0, 
        count[h]["DELETE"]+0, 
        count[h]["TOTAL"]
    }
  }
' | sort
```

---

## 五、在 MySQL 内部查询（无需文件系统权限）

如果无法直接访问 binlog 文件，可以使用：

### SHOW BINLOG EVENTS

```sql
-- 查看当前 binlog 事件类型分布
SELECT
    EVENT_TYPE,
    COUNT(*) AS cnt
FROM (
    SELECT EVENT_TYPE
    FROM mysql.binlog.000123  -- 8.0+ 不支持，需要用下面的方式
) t;

-- 实际使用 SHOW BINLOG EVENTS（需 SUPER 权限）
-- 这个方法适合小范围快速查看
SHOW BINLOG EVENTS IN 'binlog.000123' LIMIT 100;
```

### performance_schema（MySQL 8.0+）

```sql
-- 查看 statement 统计（间接反映 DML 频率）
SELECT
    DIGEST_TEXT,
    COUNT_STAR        AS exec_count,
    SUM_ROWS_AFFECTED AS total_rows_affected,
    SUM_ROWS_EXAMINED AS total_rows_examined
FROM performance_schema.events_statements_summary_by_digest
WHERE SCHEMA_NAME = 'your_database'
  AND DIGEST_TEXT REGAIN '(INSERT|UPDATE|DELETE)'
ORDER BY COUNT_STAR DESC
LIMIT 20;
```

---

## 六、快速对照表

| 场景 | 推荐方案 |
|---|---|
| 快速看单个 binlog | Shell 脚本 `grep + sort \| uniq -c` |
| 多文件 + 时间过滤 + CSV 导出 | Python 脚本 |
| 按小时发现写入热点 | `hourly_dml_stats.sh` |
| 无文件系统权限 | `performance_schema` |
| 需要实时监控 | 开启 `binlog_transaction_dependency_tracking` + 外部采集 |

### 常用参数速记

```bash
# 关键 mysqlbinlog 参数
--no-defaults                  # 跳过 my.cnf 避免干扰
--base64-output=decode-rows    # 解码 ROW 格式事件
-v (--verbose)                 # 显示行数据（-vv 显示列类型注释）
--start-datetime / --stop-datetime   # 时间过滤
--start-position / --stop-position   # 位点过滤（更精确）
--database=db_name             # 只看指定库
```

> **注意**：`-v` 与 `-vv` 的区别 —— `-vv` 会在每列前面加上列类型和注释（如 `@1=100 /* INT meta=0 nullable=0 is_null=0 */`），在做行数统计时建议用 `-v` 避免干扰 `grep` 匹配。
