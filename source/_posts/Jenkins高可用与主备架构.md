---
title: Jenkins 高可用与主备架构
date: 2026-08-23 09:45:00
tags:
  - Jenkins
  - 高可用
categories:
  - Jenkins SRE
---

Jenkins 原生无 active-active 集群，HA 靠**共享 JENKINS_HOME + 单活 Controller + 快速 failover**。

## HA 拓扑

```
                    Load Balancer (VIP/DNS)
                           │
              ┌────────────┴────────────┐
         Controller-1              Controller-2 (standby)
              │                            │
              └──────────┬─────────────────┘
                    NFS / EFS
                  JENKINS_HOME
                           │
                      Agent Pool
```

同一时刻**仅一个 Controller 写** JENKINS_HOME。

## 共享存储要求

| 要求 | 说明 |
|------|------|
| POSIX 兼容 | NFS v4、EFS、Azure Files |
| 低延迟 | 配置变更频繁 |
| 备份 | 快照 + 异地复制 |

## Failover 流程

```
1. 监控 Controller-1 健康失败
2. LB 切流量到 Controller-2
3. Controller-2 挂载同一 JENKINS_HOME 启动
4. Agent 自动重连（50000 端口指向新 Controller）
5. 验证构建队列与凭据
```

RTO 目标：5~30 分钟（视启动与 Agent 重连）。

## CloudBees HA / 企业方案

商业版支持更自动化 HA；开源方案靠运维脚本 + Keepalived。

## Agent 重连

```bash
# Agent systemd 配置 JENKINS_URL 指向 LB VIP
Environment="JENKINS_URL=https://jenkins.example.com/"
```

## 避免 split-brain

- 共享存储层排他锁
- 或使用 **Configuration as Code** 快速重建 Controller + 备份 restore

## 检查清单

- [ ] JENKINS_HOME 不在本地磁盘
- [ ] LB 健康检查 `/login` 或 `/api/json`
- [ ] failover 演练季度一次
- [ ] Agent 连 LB 而非单节点 IP
- [ ] 构建历史在共享存储可访问

**没有共享 JENKINS_HOME 的「双 Controller」会数据分裂**。
