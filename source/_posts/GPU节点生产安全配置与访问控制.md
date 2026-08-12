---
title: GPU 节点生产安全配置与访问控制
date: 2026-08-25 12:30:00
tags:
  - nvidia-smi
  - SRE
  - 安全
categories:
  - nvidia-smi SRE
---

GPU 节点算力昂贵，安全配置防止**未授权占卡、横向移动、数据泄露**。

## 访问控制

| 层 | 措施 |
|----|------|
| 网络 | GPU 节点仅内网/VPN，禁止公网 SSH |
| SSH | 堡垒机 + 密钥，禁用密码 |
| sudo | 最小权限，驱动变更需审批 |
| K8s | RBAC + Namespace 隔离 GPU 配额 |

## 多租户隔离

- **调度层**：ResourceQuota `nvidia.com/gpu`
- **运行时**：MIG 或独占节点池
- **环境变量**：禁止用户随意设置 `NVIDIA_VISIBLE_DEVICES` 绕过

## 审计

```bash
# 谁在何时执行 smi（示例 audit 规则）
# /etc/audit/rules.d/gpu.rules
-w /usr/bin/nvidia-smi -p x -k gpu_smi

# 定期导出 GPU 进程归属
nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid --format=csv
```

结合 ps/K8s owner 建立占卡审计。

## 敏感操作管控

| 操作 | 要求 |
|------|------|
| `nvidia-smi -pl` 改功耗 | 变更单 |
| `nvidia-smi -rgc/-rmc` 锁频 | 禁止生产随意使用 |
| MIG 重切 | 维护窗口 + 审批 |
| 驱动安装 | 仅自动化账号 |

## 镜像与供应链

- 仅允许内部 registry 签名镜像跑 GPU
- 扫描 CUDA 基础镜像 CVE
- 禁止 `--privileged` GPU Pod（除非白名单）

## 反模式

- GPU 节点与办公网 flat
- 共享 root 账号值班
- 无占卡审计，离职人员进程仍占显存

安全基线纳入 **GPU 节点上线 Checklist**（见本系列第 19 篇）。
