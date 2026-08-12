---
title: OpenSearch 故障演练与混沌工程
date: 2026-08-20 13:15:00
tags:
  - OpenSearch
  - 混沌工程
categories:
  - OpenSearch SRE
---

故障演练验证 HA、快照恢复与 Runbook 在真实故障下的有效性。

## 演练场景

| 场景 | 注入 | 预期 |
|------|------|------|
| data 节点宕机 | stop 1 node | yellow→green，无写入中断 |
| cluster_manager 宕机 | stop 1 master | 选举新 leader，无感知 |
| 磁盘 flood | 填满 1 节点 | 告警，blocks 触发 |
| 索引误删 | DELETE index | snapshot restore |
| AZ 故障 | 停 1 AZ 节点 | awareness 保 quorum |
| 快照恢复 | 新集群 restore | RTO 达标 |

## 节点故障演练

```bash
# staging
systemctl stop opensearch   # data-2
watch curl -s '_cluster/health'
# 验证：status yellow → 恢复节点 → green
# 记录：恢复时间、unassigned shard 数
```

## 快照恢复演练

```bash
# 1. 创建测试索引写入数据
# 2. snapshot
PUT /_snapshot/s3_repo/drill-$(date +%Y%m%d)
# 3. 删除索引
DELETE /drill-test
# 4. restore
POST /_snapshot/s3_repo/drill-xxx/_restore
{"indices": "drill-test"}
# 5. 验证文档数
```

## CCR Failover 演练

见跨集群复制篇，季度执行。

## 混沌工具

- **Chaos Mesh**：Pod kill、IO delay、网络分区
- **手动**：iptables 阻断 9300

## Game Day

```
09:00  Briefing
09:30  data node failure
11:00  snapshot restore
14:00  disk flood 模拟
16:00  Postmortem
```

## 成功标准

- [ ] RTO/RPO 实测 ≤ SLA
- [ ] 告警 5 分钟内触发
- [ ] Runbook 可独立执行
- [ ] 无未预期数据永久丢失

**未演练的 snapshot/CCR 不可信**。
