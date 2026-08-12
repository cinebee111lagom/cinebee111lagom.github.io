---
title: Ceph RGW 生产运维与多站点入门
date: 2026-08-31 12:30:00
tags:
  - Ceph
  - SRE
  - RGW
categories:
  - Ceph SRE
---

RGW 生产关注 **可用、配额、生命周期、多站点**。

## HA 部署

```
                LB (HAProxy/nginx)
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
     RGW:1       RGW:2       RGW:3
        └───────────┼───────────┘
                    ▼
              RADOS (EC/replicated pool)
```

```bash
ceph orch apply rgw prod --placement="3:label:rgw" --port=443 --ssl=true
```

## 配额

```bash
radosgw-admin quota set --quota-scope=bucket --max-size=100G --uid=tenant1
radosgw-admin quota enable --quota-scope=bucket --uid=tenant1
```

## 生命周期

自动转冷存储、过期删除，控制容量（见容量治理篇）。

## 多站点（灾备）

| 模式 | RPO |
|------|-----|
| sync | 近 0 |
| async | 分钟~小时 |

需 **Realm/Zonegroup/Zone** 规划，变更复杂，维护窗口操作。

## 监控

- RGW 请求 5xx 率
- bucket 容量 Top N
- 延迟 P99

## 反模式

- 单 RGW 无 LB
- public bucket 误开
- 无 lifecycle 导致对象堆积

对象业务 **单独 pool + EC** 降成本。
