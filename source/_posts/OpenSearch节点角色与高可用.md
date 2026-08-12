---
title: OpenSearch 节点角色与高可用
date: 2026-08-20 09:45:00
tags:
  - OpenSearch
  - 高可用
categories:
  - OpenSearch SRE
---

OpenSearch 高可用依赖 **cluster_manager 选举**、**副本分片** 与合理的节点角色分离。

## cluster_manager 节点

- 管理集群元数据、索引创建、分片分配
- 生产 **3 个专用** cluster_manager（不存数据）
- 配置：

```yaml
node.roles: [cluster_manager]
node.attr: temp: hot
```

## 数据节点与副本

```
Index: 3 primary + 1 replica
→ 每个 primary 有 1 副本分布在其他 data 节点
→ 允许 1 个 data 节点故障不影响数据
```

```bash
PUT /logs-2026.08.20
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1
  }
}
```

## 跨 AZ 部署

```yaml
# 节点打 zone 属性
node.attr.zone: ap-southeast-1a

# 分片感知分配
cluster.routing.allocation.awareness.attributes: zone
```

副本自动跨 AZ 分布。

## 脑裂防护

- cluster_manager 节点数为奇数
- `discovery.seed_hosts` 稳定
- 2.x 基于 cluster_manager term，优于旧 master 机制

## 故障场景

| 故障 | 影响 | 恢复 |
|------|------|------|
| 1 data 节点 down | yellow，副本提升 | 替换节点，自动 reassign |
| 1 cluster_manager down | 无影响（quorum 2/3） | 替换节点 |
| 2 data 节点 down | 可能 red | 紧急恢复节点或 restore snapshot |
| 磁盘满 | 只读模式 | 扩磁盘、删索引、ISM |

## 只读保护

磁盘 watermark 触发：

```
flood_stage → 索引 blocks.read_only_allow_delete
```

```bash
GET /_cluster/settings?include_defaults=true&filter_path=*.watermark*
```

## 检查清单

- [ ] replicas ≥ 1（生产）
- [ ] cluster_manager 与 data 分离（大规模）
- [ ] 跨 AZ awareness 已配置
- [ ] 磁盘 watermark 监控告警
- [ ] 季度节点故障演练

**无副本的 OpenSearch 不是 HA**。
