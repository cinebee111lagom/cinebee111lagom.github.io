---
title: OpenSearch 分词与分析器入门
date: 2026-08-19 11:00:00
tags:
  - OpenSearch
  - 分词
  - Analyzer
categories:
  - OpenSearch 入门
---

全文搜索的质量取决于**分词（Analysis）**，中文场景尤其需要关注。

## 分析器组成

```
Analyzer = Character Filter + Tokenizer + Token Filter
```

| 组件 | 作用 |
|------|------|
| Character Filter | 预处理（HTML  strip） |
| Tokenizer | 切分 token |
| Token Filter | 小写、停用词、同义词 |

## 内置分析器

| 名称 | 说明 |
|------|------|
| standard | 默认，按 Unicode 分词 |
| simple | 按非字母切分 |
| whitespace | 按空格 |
| keyword | 整句一个 token |

## 测试分词

```bash
GET /_analyze
{
  "analyzer": "standard",
  "text": "OpenSearch is awesome"
}

GET /products/_analyze
{
  "field": "title",
  "text": "OpenSearch 入门指南"
}
```

## 中文分词（ICU / SmartCN）

OpenSearch 可安装 **analysis-icu** 或 **analysis-smartcn** 插件：

```bash
# Docker 内
bin/opensearch-plugin install analysis-smartcn
```

```json
"title": {
  "type": "text",
  "analyzer": "smartcn"
}
```

## 自定义分析器

```bash
PUT /products
{
  "settings": {
    "analysis": {
      "analyzer": {
        "my_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "stop"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "my_analyzer"
      }
    }
  }
}
```

## search_analyzer vs analyzer

```json
"title": {
  "type": "text",
  "analyzer": "smartcn",           // 索引时分词
  "search_analyzer": "smartcn"     // 搜索时分词
}
```

索引与搜索分析器不一致时，需确保 token 可对齐。

## 常见问题

| 问题 | 原因 |
|------|------|
| 搜不到中文 | 未装中文分词插件 |
| 搜 A 出现 B | 分词过粗/同义词 |
| 大小写不一致 | 加 lowercase filter |

中文搜索项目**务必在 mapping 阶段确定分析器**，后期改需 reindex。
