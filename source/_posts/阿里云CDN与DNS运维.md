---
title: 阿里云 CDN 与 DNS 运维
date: 2026-08-26 12:30:00
tags:
  - 阿里云
  - CDN
  - DNS
categories:
  - 阿里云资源 SRE
---

CDN 与 DNS 是用户访问入口，SRE 需保障解析正确、证书有效与回源健康。

## 云解析 DNS

```
主域名：example.com
  A/AAAA  → SLB/ALB（TTL 300）
  CNAME   → CDN 域名
  私有域： internal.example.com（VPC 内）
```

## 高可用 DNS

```
DNS 负载均衡（权重/地域）
健康检查：失败自动摘除
多线路：电信/联通/移动（可选）
```

## CDN 配置

```
源站：OSS 或 SLB/ALB
HTTPS：开启 HTTP/2
缓存规则：
  /static/*  缓存 30 天
  /api/*     不缓存
压缩：Gzip/Brotli
```

## 证书

```
CDN 托管证书 或 上传
到期前 30 天告警
Let's Encrypt 自动续期（Function Compute）
```

## 监控

| 指标 | 告警 |
|------|------|
| 回源 5xx 率 | P1 |
| 带宽突增 | P2（攻击或热点） |
| 命中率下降 | P2 |

## 安全

```
WAF 前置（可选）
DDoS 高防（大促）
Referer 防盗链
URL 鉴权（敏感资源）
```

## 故障：CDN 回源失败

```
1. 源站 SLB 健康检查
2. CDN 回源 Host 是否正确
3. 源站安全组是否允许 CDN 回源 IP 段
4. OSS Bucket 权限
```

## Checklist

- [ ] DNS TTL 合理（切流 vs 缓存）
- [ ] HTTPS 全站
- [ ] 回源超时配置
- [ ] 预热大促静态资源

CDN/DNS 故障影响**全部用户**，变更需谨慎。
