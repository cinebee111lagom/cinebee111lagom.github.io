---
title: DCGM Python API 绑定入门
date: 2026-08-23 13:30:00
tags:
  - DCGM
  - Python
  - API
categories:
  - DCGM 新手入门
---

除 CLI 和 exporter 外，可通过 **Python pydcgm** 编写自定义监控程序。

## 安装

```bash
# 通常随 DCGM 包提供，或
pip install pydcgm  # 视发行版，可能需 NVIDIA 仓库
```

需 Host Engine 运行。

## 基础示例

```python
import pydcgm

# 连接 Host Engine
dcgm = pydcgm.DcgmHandle(ipAddress="127.0.0.1", opMode=pydcgm.DCGM_OPERATION_MODE_AUTO)

# 获取 GPU 数量
gpu_ids = dcgm.discovery.GetAllSupportedGpuIds()
print(f"Found {len(gpu_ids)} GPUs: {gpu_ids}")

# 创建 Group
group = pydcgm.DcgmGroup(dcgm, groupName="mygroup", groupType=pydcgm.DCGM_GROUP_EMPTY)
for gid in gpu_ids:
    group.AddGpu(gid)

# 读取字段（GPU 温度示例 fieldId）
field_id = pydcgm.DCGM_FI_DEV_GPU_TEMP
values = dcgm.health.WatchFields(group.handle, [field_id])
```

> API 随 DCGM 版本变化，以官方 `pydcgm` 文档为准。

## 使用场景

| 场景 | 说明 |
|------|------|
| 定制 exporter | 特殊 label 逻辑 |
| 训练平台集成 | Job 起止采集 |
| 自动化运维 | 健康检查 + 自动 cordon |
| 计费系统 | 周期性采样写 DB |

## 与 Prometheus 关系

- 生产通用指标：**dcgm-exporter** 足够
- 定制逻辑：Python 写 DB/API，exporter 仍保留

## 错误处理

```python
try:
    dcgm = pydcgm.DcgmHandle(ipAddress="127.0.0.1")
except pydcgm.DcgmException as e:
    print(f"DCGM error: {e}")
```

## 替代：调用 dcgmi

简单场景可用 subprocess：

```python
import subprocess
import json

out = subprocess.check_output(["dcgmi", "discovery", "-l"], text=True)
print(out)
```

稳定但性能不如原生 API。

新手优先 **dcgm-exporter**，有定制需求再学 pydcgm。
