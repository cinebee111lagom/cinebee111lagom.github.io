---
title: Ceph 版本升级与滚动迁移 SRE 流程
date: 2026-08-31 10:45:00
tags:
  - Ceph
  - SRE
  - 升级
categories:
  - Ceph SRE
---

Ceph 升级需 **逐版本、逐 daemon、可回滚**，不可跨 major 跳跃。

## 升级路径

```
Quincy 17.2.x → Reef 18.2.x → Squid 19.x
（以官方 Upgrade Guide 为准）
```

## 升级前

- [ ] 全集群 HEALTH_OK（或仅已知 WARN）
- [ ] `ceph versions` 统一
- [ ] 备份 + crush/config
- [ ] staging 同路径验证

## cephadm 滚动升级

```bash
# 设置目标版本
ceph orch upgrade start --image quay.io/ceph/ceph:v18.2.0

# 监控进度
ceph orch upgrade status
watch ceph -s
```

cephadm 按 **MON → MGR → OSD → others** 顺序滚动。

## 手动节点升级（概念）

```
1. ceph osd set noout          # 可选，减少 rebalance
2. drain 单节点 daemon
3. 升级容器镜像
4. 验证 ceph -s
5. 下一节点
6. ceph osd unset noout
```

## 回滚

- 升级未完成：`ceph orch upgrade stop`
- 已升级需降版本：**困难**，依赖 backup restore
- **staging 必须先走一遍**

## 兼容性

| 检查 | |
|------|---|
| K8s CSI 版本 | 兼容矩阵 |
| Linux 内核 | BlueStore 要求 |
| OpenStack 版本 | Cinder 支持 |

## 反模式

- 生产首个 major 升级无 staging
- 升级窗口做 OSD 扩容
- 忽略 `require_osd_release`

升级 Runbook 归档每版本 **问题与耗时**。
