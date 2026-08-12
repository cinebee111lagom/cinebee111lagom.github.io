---
title: nvidia-smi 格式化输出：CSV 与 XML
date: 2026-08-24 11:45:00
tags:
  - nvidia-smi
  - CSV
categories:
  - nvidia-smi 新手入门
---

`--query` + `--format` 让 nvidia-smi 输出可被脚本和程序轻松解析。

## CSV 格式

```bash
nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total \
  --format=csv

# 无表头、无单位（便于 awk）
nvidia-smi --query-gpu=index,utilization.gpu,memory.used \
  --format=csv,noheader,nounits
```

## 常用 query 字段

| 字段 | 说明 |
|------|------|
| index | GPU 编号 |
| name | 型号 |
| uuid | 唯一 ID |
| driver_version | 驱动版本 |
| temperature.gpu | 温度 |
| utilization.gpu | GPU 利用率 |
| utilization.memory | 内存带宽利用率 |
| memory.used / memory.total | 显存 |
| power.draw / power.limit | 功耗 |
| clocks.current.sm | 当前 SM 时钟 |
| ecc.errors.corrected.volatile.total | ECC |

完整列表：

```bash
nvidia-smi --help-query-gpu
nvidia-smi --help-query-compute-apps
```

## 查询进程 CSV

```bash
nvidia-smi --query-compute-apps=gpu_bus_id,pid,process_name,used_gpu_memory \
  --format=csv,noheader
```

## XML 格式

```bash
nvidia-smi -q -x > gpu-info.xml
nvidia-smi --query-gpu=name,memory.total --format=xml
```

适合 Python `xml.etree` 解析。

## Bash 脚本示例

```bash
#!/bin/bash
while IFS=, read -r idx util mem; do
  util=$(echo $util | tr -d ' ')
  mem=$(echo $mem | tr -d ' ')
  if [ "$util" -gt 90 ]; then
    echo "GPU $idx high util: ${util}%"
  fi
done < <(nvidia-smi --query-gpu=index,utilization.gpu,memory.used \
  --format=csv,noheader,nounits)
```

## Python 示例

```python
import subprocess
import csv
from io import StringIO

out = subprocess.check_output([
    "nvidia-smi",
    "--query-gpu=index,utilization.gpu,memory.used",
    "--format=csv,noheader,nounits",
], text=True)
for row in csv.reader(StringIO(out)):
    idx, util, mem = row
    print(f"GPU {idx}: {util}% util, {mem} MiB")
```

格式化输出是 **nvidia-smi 自动化** 的核心技能。
