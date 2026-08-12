---
title: nvidia-smi 实战：GPU 节点日常巡检脚本
date: 2026-08-24 13:30:00
tags:
  - nvidia-smi
  - 实战
  - 巡检
categories:
  - nvidia-smi 新手入门
---

用 nvidia-smi 编写一个实用的 GPU 节点日常巡检脚本。

## 巡检脚本

```bash
#!/bin/bash
# gpu-check.sh - GPU 节点日常巡检
set -euo pipefail

WARN_TEMP=83
WARN_UTIL=0
FAIL=0

echo "========== GPU Check $(date) =========="
echo "Host: $(hostname)"

# 1. 驱动与 smi
if ! nvidia-smi &>/dev/null; then
  echo "[FAIL] nvidia-smi 不可用"
  exit 1
fi

echo "[OK] Driver: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)"
echo "GPU Count: $(nvidia-smi -L | wc -l)"
echo

# 2. 逐卡检查
while IFS=, read -r idx name temp util mem_used mem_total power; do
  idx=$(echo $idx | tr -d ' ')
  temp=$(echo $temp | tr -d ' ')
  util=$(echo $util | tr -d ' ')
  mem_pct=$(( mem_used * 100 / mem_total ))

  status="OK"
  [ "$temp" -gt "$WARN_TEMP" ] && status="WARN: high temp" && FAIL=1
  [ "$mem_pct" -gt 95 ] && status="WARN: mem full" && FAIL=1

  echo "GPU $idx ($name): ${temp}C, util=${util}%, mem=${mem_pct}%, power=${power}W [$status]"
done < <(nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw \
  --format=csv,noheader,nounits)

echo

# 3. 进程
echo "--- Processes ---"
nvidia-smi --query-compute-apps=gpu_bus_id,pid,process_name,used_gpu_memory \
  --format=csv,noheader 2>/dev/null || echo "No compute processes"

# 4. ECC
echo
echo "--- ECC (uncorrected) ---"
nvidia-smi --query-gpu=index,ecc.errors.uncorrected.aggregate.total \
  --format=csv,noheader | while read line; do
  echo "$line"
  echo "$line" | grep -qv ", 0$" && FAIL=1
done

# 5. XID
echo
echo "--- Recent XID (dmesg) ---"
dmesg 2>/dev/null | grep -i "Xid" | tail -3 || echo "None recent"

echo
[ "$FAIL" -eq 0 ] && echo "========== PASS ==========" || echo "========== WARN/FAIL =========="
exit $FAIL
```

## 使用

```bash
chmod +x gpu-check.sh
./gpu-check.sh

# cron 每日 8 点
0 8 * * * /opt/scripts/gpu-check.sh >> /var/log/gpu-check.log 2>&1
```

## 扩展

- 接入 Prometheus：改用 dcgm-exporter
- 飞书/Slack 告警：FAIL 时 curl webhook
- Ansible 批量跑所有 GPU 节点

## 检查项覆盖

| 项 | 命令来源 |
|----|----------|
| 驱动 | --query-gpu=driver_version |
| 温度/利用率/显存 | --query-gpu |
| 进程 | --query-compute-apps |
| ECC | ecc.errors.uncorrected |
| XID | dmesg |

这个脚本是 **smi 系列技能的综合练习**。
