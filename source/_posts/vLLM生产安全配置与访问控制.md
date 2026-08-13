---
title: vLLM 生产安全配置与访问控制
date: 2026-09-04 11:00:00
tags:
  - vLLM
  - SRE
  - 安全
categories:
  - vLLM SRE
---

推理服务常能接触 **企业内部数据**，安全与鉴权是上线门禁。

## 认证

| 层 | 措施 |
|----|------|
| vLLM | `--api-key` 或环境变量 |
| 网关 | OAuth2/JWT、mTLS |
| 网络 | 仅内网 / 零信任 |

```bash
vllm serve MODEL --api-key "$VLLM_API_KEY"
```

应用侧使用 **独立密钥**，禁止共用 root 式全局 key。

## 授权与隔离

| 风险 | 控制 |
|------|------|
| 越权用大模型 | 网关按租户路由允许的 model |
| Prompt 注入/泄密 | 应用层过滤 + 审计 |
| 模型权重泄露 | 节点权限、镜像私有仓 |
| 日志泄密 | 脱敏，勿打完整用户输入到公开日志 |

## TLS

- 边缘终止 TLS（Ingress/Nginx）
- 内网也可 mTLS（高安全场景）

## 供应链

- 镜像来自内部仓库，pin digest  
- 模型校验 checksum / 签名  
- 禁止生产节点临时 `pip install`  

## 审计

记录：`who / when / model / tokens / client_ip / status`  
保留期按合规要求。

## 反模式

- 8000 端口对公网
- API key 写进前端
- 日志全文落盘含身份证/密钥

安全配置纳入 **上线 Checklist**。
