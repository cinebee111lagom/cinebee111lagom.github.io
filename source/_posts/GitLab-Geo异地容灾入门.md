---
title: GitLab Geo 异地容灾入门
date: 2026-08-29 12:45:00
tags:
  - GitLab
  - SRE
  - Geo
categories:
  - GitLab SRE
---

**GitLab Geo** 提供只读副本站点，用于 **就近访问、灾备、合规数据驻留**。

## 架构

```
Primary（写）──复制──→ Secondary（读）
   │                        │
 用户 push/MR            用户 clone/pull（只读）
```

## 适用场景

| 场景 | 说明 |
|------|------|
| 跨国团队 | 本地 Secondary 加速 clone |
| DR | Primary 故障提升 Secondary |
| 合规 | 数据留在指定区域 |

## 组件要求

- Primary/Secondary 均 **EE 授权**（Geo 为企业功能）
- 网络：Secondary 可连 Primary API/DB/Gitaly
- 对象存储：跨区复制或统一 backend

## 关键配置（概念）

```ruby
# Primary
gitlab_rails['geo_node_name'] = 'primary'
roles ['geo_primary_role']

# Secondary
gitlab_rails['geo_node_name'] = 'secondary'
roles ['geo_secondary_role']
gitlab_rails['geo_registry_replication_enabled'] = true
```

## 监控

| 指标 | 告警 |
|------|------|
| geo replication lag | > 15min P1 |
| geo status | failed |
| event cursor lag | 积压 |

## Failover（计划内）

```
1. 停止 Primary 写入
2. geo promote secondary
3. DNS 切到 Secondary
4. 验证 push/MR/Pipeline
```

**Failover 演练**半年一次。

## 反模式

- 把 Geo 当备份唯一手段
- Secondary 当 Primary 双写
- 不监控 replication lag

无 EE 可用 **定时 backup offsite + 冷备恢复** 替代。
