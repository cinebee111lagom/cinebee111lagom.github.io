---
title: OpenSearch 生产集群部署实战
date: 2026-08-20 09:30:00
tags:
  - OpenSearch
  - 部署
categories:
  - OpenSearch SRE
---

三节点生产集群部署示例（裸机/Docker Compose 思路，生产可换 Ansible/K8s）。

## 节点规划

| 节点 | 角色 | 规格参考 |
|------|------|----------|
| os-1~3 | cluster_manager,data,ingest | 8C32G + 500GB SSD |

## opensearch.yml（每节点差异）

```yaml
cluster.name: prod-opensearch
node.name: os-1
node.roles: [cluster_manager, data, ingest]

network.host: 0.0.0.0
http.port: 9200
transport.port: 9300

discovery.seed_hosts: ["os-1:9300", "os-2:9300", "os-3:9300"]
cluster.initial_cluster_manager_nodes: ["os-1", "os-2", "os-3"]

path.data: /var/lib/opensearch/data
path.logs: /var/log/opensearch

plugins.security.ssl.http.enabled: true
plugins.security.ssl.transport.enabled: true
```

## JVM

```bash
# jvm.options
-Xms16g
-Xmx16g
```

堆 = 物理内存 50%，且 ≤ 32GB。

## 系统参数

```bash
sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' >> /etc/sysctl.conf
ulimit -n 65536
```

## 验证集群

```bash
curl -ku admin:password https://os-1:9200/_cluster/health?pretty
curl -ku admin:password https://os-1:9200/_cat/nodes?v
```

期望 `status: green`，3 节点可见。

## 初始配置

```bash
# 集群级设置
PUT /_cluster/settings
{
  "persistent": {
    "action.auto_create_index": false
  }
}
```

禁止自动创建索引，强制走模板。

## 部署检查清单

- [ ] cluster_manager 节点奇数（3）
- [ ] 种子节点与 initial_cluster_manager_nodes 一致
- [ ] Security 插件 TLS 已配置
- [ ] 数据目录独立磁盘
- [ ] 防火墙仅内网 9200/9300

## 常见问题

| 问题 | 解决 |
|------|------|
| 无法组成集群 | discovery 配置、9300 互通 |
| bootstrap 失败 | 清 data 目录重来（仅新集群） |
| yellow | 单副本未分配，加节点或 replicas=0 |

生产 **≥3 节点** 是 HA 底线。
