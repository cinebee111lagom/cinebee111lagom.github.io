---
title: ArgoCD SRE 上线 Checklist 与生产 Runbook
date: 2026-08-27 13:30:00
tags:
  - ArgoCD
  - SRE
  - Runbook
categories:
  - ArgoCD SRE
---

## 上线 Checklist

### 架构

- [ ] HA：server/repo-server ≥ 2，Redis HA
- [ ] Ingress + TLS 有效
- [ ] Hub-Spoke 集群全部注册连通
- [ ] PDB 已配置

### 安全

- [ ] SSO 启用，admin 本地账号禁用
- [ ] RBAC policy 已评审
- [ ] AppProject 按团队/环境隔离
- [ ] exec/Web Terminal 禁用
- [ ] NetworkPolicy 已应用

### Secret

- [ ] Git repo credential 安全存储
- [ ] cluster token 最小权限
- [ ] Sealed Secrets / External Secrets 就绪
- [ ] break-glass 流程文档化

### 监控

- [ ] Prometheus 采集所有 metrics Service
- [ ] Grafana Dashboard（14584）
- [ ] P0/P1 告警 + Runbook 链接
- [ ] audit log 接入 SIEM

### 备份与 DR

- [ ] Velero 或 secret 定期备份
- [ ] App of Apps bootstrap 在 Git
- [ ] 3 个月内 DR restore 演练成功

### 治理

- [ ] ApplicationSet 或应用创建规范
- [ ] prod sync 策略（manual + PR）
- [ ] syncWindow 配置

---

## 日常 Runbook

| 频率 | 动作 |
|------|------|
| 每日 | 看 P0/P1 告警、Degraded prod app |
| 每周 | OutOfSync > 7d 清单、Git 凭证有效期 |
| 每月 | 集群 token 审计、僵尸 Application 清理 |
| 每季 | 升级 staging、故障演练、DR 演练 |

## 应急

| 事件 | 动作 |
|------|------|
| 控制面全挂 | 查 Ingress/Pod/Redis → Helm rollback |
| prod 误发布 | Git revert → argocd app sync |
| 大规模 Sync Failed | repo-server 日志 → 凭证/Git |
| cluster 断连 | 网络/证书/token 轮换 |

## 反模式

- Checklist 未执行即接 prod 流量
- 无 on-call Runbook
- 备份未验证 restore

配合 **ArgoCD 新手入门** 系列：入门练操作，SRE 管生产。
