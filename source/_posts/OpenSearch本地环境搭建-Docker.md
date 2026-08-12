---
title: OpenSearch 本地环境搭建（Docker）
date: 2026-08-19 09:15:00
tags:
  - OpenSearch
  - Docker
  - 环境
categories:
  - OpenSearch 入门
---

Docker 是本地学习 OpenSearch 最快的方式，一条命令即可启动单节点集群。

## docker-compose 单节点

```yaml
# docker-compose.yml
services:
  opensearch:
    image: opensearchproject/opensearch:2.14.0
    environment:
      - discovery.type=single-node
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
      - DISABLE_SECURITY_PLUGIN=true   # 本地学习可关闭安全插件
    ports:
      - "9200:9200"
      - "9600:9600"
    volumes:
      - opensearch-data:/usr/share/opensearch/data

  dashboards:
    image: opensearchproject/opensearch-dashboards:2.14.0
    ports:
      - "5601:5601"
    environment:
      - OPENSEARCH_HOSTS=["http://opensearch:9200"]
      - DISABLE_SECURITY_DASHBOARDS_PLUGIN=true
    depends_on:
      - opensearch

volumes:
  opensearch-data:
```

```bash
docker compose up -d
```

## 验证

```bash
curl http://localhost:9200

# 期望返回 cluster_name、version 等 JSON
curl http://localhost:9200/_cluster/health?pretty
```

浏览器打开 **http://localhost:5601** 进入 Dashboards。

## 开启安全（更接近生产）

```yaml
environment:
  - OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin_12345!
# 移除 DISABLE_SECURITY_PLUGIN
# 访问需 HTTPS + 用户名 admin
```

```bash
curl -ku admin:Admin_12345! https://localhost:9200
```

## 常用端口

| 端口 | 用途 |
|------|------|
| 9200 | REST API |
| 9600 | Performance Analyzer |
| 5601 | Dashboards |

## 内存要求

- 最少 **512MB** JVM（学习）
- 生产单节点建议 **4GB+**
- 若启动失败，调大 `OPENSEARCH_JAVA_OPTS`

## 常见问题

| 问题 | 解决 |
|------|------|
| vm.max_map_count 不足 | `sysctl -w vm.max_map_count=262144` |
| 内存 OOM | 减小 `-Xmx` 或加 Docker 内存 |
| Dashboards 连不上 | 检查 OPENSEARCH_HOSTS |

下一篇讲 Index、Document、Shard 等核心概念。
