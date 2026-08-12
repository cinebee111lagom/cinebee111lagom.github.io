---
title: OpenSearch 版本升级与滚动迁移
date: 2026-08-20 12:00:00
tags:
  - OpenSearch
  - 升级
categories:
  - OpenSearch SRE
---

OpenSearch 升级需 **滚动重启**，大版本需兼容性测试与快照兜底。

## 升级前

```bash
GET /_cluster/health   # 必须 green
PUT /_snapshot/s3_repo/pre-upgrade-$(date +%Y%m%d)
# staging 同版本路径验证
```

## 滚动升级顺序

```
1. 升级 non-cluster_manager 节点（data/ingest）
2. 逐个升级 cluster_manager 节点（最后）
3. 每节点：停止 → 换二进制/镜像 → 启动 → 等 green
```

## 裸机示例

```bash
systemctl stop opensearch
# 替换 /usr/share/opensearch
systemctl start opensearch
curl -ku admin:pass https://localhost:9200/_cluster/health?wait_for_status=green&timeout=60s
```

## K8s Operator

```yaml
spec:
  general:
    version: 2.15.0
```

Operator 自动滚动；观察 `OpenSearchCluster` status。

## 兼容性

- 阅读 Release Notes（breaking changes）
- Dashboards 版本与 OpenSearch 对齐
- 插件（security、s3、ism）版本匹配

## 跨大版本

```
2.11 → 2.14 → 2.15 逐级
或 snapshot restore 到新集群
```

## 回滚

- 保留旧版本镜像/包
- 升级前 snapshot
- 回滚 = 降版本 + 重启（同 major 通常可行）

## Checklist

- [ ] 集群 green
- [ ] 快照完成
- [ ] staging 验证通过
- [ ] 低峰窗口
- [ ] On-Call 待命
- [ ] 回滚方案就绪

**升级前 snapshot，升级后验证搜索与写入**。
