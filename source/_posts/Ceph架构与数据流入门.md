---
title: Ceph 架构与数据流入门
date: 2026-08-30 09:30:00
tags:
  - Ceph
  - 架构
  - 入门
categories:
  - Ceph 新手入门
---

一次 **RBD 写入** 走通全链路，架构就不再抽象。

## 写入流程（简化）

```
1. Client 向 MON 订阅/获取 Cluster Map
2. Client 计算 object → PG（CRUSH）
3. Client 直接连接 Primary OSD 写入
4. Primary OSD 复制到 Secondary OSD（副本 pool）
5. 全部 ACK 后返回 Client 成功
```

**特点**：Client 与 OSD **直接通信**，MON 不参与数据路径。

## 读取流程

```
Client → 算 PG → 连 Primary OSD → 读 object → 返回
```

## 组件拓扑（最小生产）

```
         ┌──── MON ×3 ────┐
         │   MGR ×2       │
         └───────┬────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
 OSD node1    OSD node2    OSD node3
 (NVMe/HDD)   (NVMe/HDD)   (NVMe/HDD)
```

## 副本 vs 纠删码

| 类型 | 说明 | 适用 |
|------|------|------|
| 副本（replicated） | 3 副本默认 | RBD、通用 |
| 纠删码（EC） | k+m 条带 | 冷数据、对象 |

新手先掌握 **3 副本 replicated pool**。

## 网络建议

| 网络 | 用途 |
|------|------|
| Public | Client ↔ OSD |
| Cluster | OSD ↔ OSD 复制/恢复 |

生产 **复制流量走独立网络**，避免打满业务网。

## 控制面 vs 数据面

| 控制面 | 数据面 |
|--------|--------|
| MON、MGR、cephadm | OSD 读写 |
| 故障影响元数据 | 故障影响 IO |

## 反模式

- 单网卡扛复制+业务
- 以为数据经过 MON（性能瓶颈误解）

下一篇：**安装与环境准备**。
