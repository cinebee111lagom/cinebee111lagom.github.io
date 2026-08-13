---
title: vLLM 生产高可用与负载均衡
date: 2026-09-04 09:30:00
tags:
  - vLLM
  - SRE
  - HA
categories:
  - vLLM SRE
---

vLLM 单进程挂掉即中断服务，生产需 **多副本或快速拉起 + 健康检查**。

## HA 策略

| 场景 | 策略 |
|------|------|
| 小模型 | ≥2 副本 + Service/LB |
| 大模型 TP | 同机多卡单副本 + 节点反亲和难；靠快速重建 + 备用池 |
| 跨 AZ | 每 AZ 独立部署，DNS/网关容灾 |

## 健康检查

```bash
curl -f http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models
```

| 探针 | 建议 |
|------|------|
| liveness | `/health`，失败重启 |
| readiness | `/health` + 模型已加载，启动宽限期长 |

大模型加载可能 **数分钟**，`initialDelaySeconds` 要够。

## Nginx 示例

```nginx
upstream vllm {
    least_conn;
    server 10.0.1.11:8000 max_fails=2 fail_timeout=30s;
    server 10.0.1.12:8000 max_fails=2 fail_timeout=30s;
}
server {
    listen 443 ssl;
    location / {
        proxy_pass http://vllm;
        proxy_read_timeout 300s;
        proxy_buffering off;  # 流式
    }
}
```

## 会话与流式

- 无状态 API，可任意后端
- SSE 流式需关闭缓冲、拉长超时
- 重试只对 **幂等/失败未产生副作用** 的请求谨慎开启

## 反模式

- readiness 在模型未加载完就接流量 → 5xx 风暴
- 流式被代理缓冲成「一次性返回」
- TP 多卡服务当无状态随意水平扩（需整组 GPU）

季度做一次 **杀 Pod/节点** 演练。
