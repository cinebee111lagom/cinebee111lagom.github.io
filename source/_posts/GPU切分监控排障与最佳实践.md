---
title: GPU 切分监控、排障与最佳实践
date: 2026-08-13 13:30:00
tags:
  - GPU切分
  - 监控
  - 运维
categories:
  - GPU切分
---

GPU 切分上线后，监控粒度从「整卡」变为「实例 / 租户」，排障思路也需相应调整。

## 监控指标

### MIG 实例级

```bash
nvidia-smi mig -gi
dcgm-exporter  # DCGM_FI_DEV_FB_USED, GPU_UTIL per GPU instance
```

### K8s 级

- Pod 请求的 `nvidia.com/mig-*` vs 节点 allocatable
- MIG 实例分配率 = allocated / total instances
- Pending Pod 因 MIG 不足的数量

### 业务级

- 每租户推理 P99 延迟
- 每路转码 FPS
- OOM / CUDA error 计数 per Pod

## 常见故障

| 现象 | 原因 | 处理 |
|------|------|------|
| 实例显存够用但 OOM | 未走 MIG，整卡多进程 | 检查 Device Plugin 分配 |
| MIG 实例数少于预期 | profile 配置错误 | 重建 mig-parted-config |
| 利用率低 | profile 过大 | 改用小 profile 提高密度 |
| NVENC 失败 | 实例无编码引擎 | 换支持 NVENC 的 profile |
| MPS 全体崩溃 | 一客户端 OOM | 迁移到 MIG 或整卡 |

## 排障命令

```bash
# 节点 MIG 拓扑
nvidia-smi -i 0 -q | grep -A 20 "MIG Mode"

# Pod 可见 GPU
kubectl exec pod -- nvidia-smi

# Device Plugin 日志
kubectl logs -n gpu-operator -l app=nvidia-device-plugin
```

## 最佳实践清单

1. **压测定 profile**：按 peak 显存 + 15% 余量选 MIG 规格
2. **一实例一主进程**：避免 MIG 实例内多进程
3. **节点池分离**：训练整卡池 / 推理 MIG 池
4. **变更 MIG 需 drain**：避免运行中 Pod 被断
5. **文档化 profile 映射**：团队共识「什么任务用什么 profile」
6. **定期审计利用率**：allocated vs 实际 fb_used，识别 over-provision

## 与调度器配合

- Volcano Queue capability 按 MIG 资源名配置
- 集群 autoscaler 感知 MIG 实例而非整卡
- 优先级抢占时按 MIG 实例粒度释放

---

本系列十篇覆盖 GPU 切分从入门、MIG/vGPU/MPS、选型、K8s 配置、视频/推理场景到监控运维。建议配合「GPU 调度」「Volcano」系列一起阅读。
