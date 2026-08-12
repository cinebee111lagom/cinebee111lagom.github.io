---
title: Ceph 新手学习路径与入门 Checklist
date: 2026-08-30 13:45:00
tags:
  - Ceph
  - 入门
  - 学习路径
categories:
  - Ceph 新手入门
---

## 推荐学习路径

```
第 1 周：概念 + 架构 + 环境准备
  └─ 篇 1~4

第 2 周：cephadm 部署 + Pool + RBD
  └─ 篇 5~7、10

第 3 周：CephFS/RGW + 健康/OSD/CRUSH
  └─ 篇 8~9、11~13

第 4 周：K8s CSI + 监控 + 快照/EC
  └─ 篇 14~18

第 5 周：排查 + OpenStack + Checklist
  └─ 篇 19~20
```

## 入门 Checklist

### 基础

- [ ] 理解 MON/OSD/PG/RADOS 关系
- [ ] 3 节点 cephadm 集群 HEALTH_OK
- [ ] 会 `ceph -s`、`ceph osd tree`、`ceph df`
- [ ] Dashboard 可登录

### 存储接口

- [ ] 创建 replicated pool 并 enable rbd
- [ ] RBD 创建/映射/挂载成功
- [ ] （可选）CephFS 挂载或 RGW S3 上传

### 运维

- [ ] 添加过 1 块新 OSD
- [ ] 读懂 WARN/ERR health detail
- [ ] Prometheus 能 scrape ceph metrics

### 进阶

- [ ] K8s StorageClass + PVC 测试
- [ ] 创建 RBD 快照与 clone
- [ ] 理解副本 vs 纠删码选型

## 配套练习

| 练习 | 技能点 |
|------|--------|
| 3 节点最小集群 | cephadm bootstrap |
| 10G RBD 读写 | rbd map + fio |
| 模拟 OSD out | 安全下线流程 |
| import Grafana 12239 类 dashboard | 监控 |
| PVC Pod 读写 | CSI |

## 推荐资源

- [Ceph 官方文档](https://docs.ceph.com/)
- [cephadm 快速开始](https://docs.ceph.com/en/quincy/cephadm/)
- [Ceph CSI](https://github.com/ceph/ceph-csi)

## 延伸（后续可学）

- **Ceph SRE 系列**（升级、备份、性能调优、故障演练）
- **Rook**（K8s 内运行 Ceph Operator）
- **MinIO vs RGW** 对象存储选型

---

**Ceph 新手入门系列 20 篇**完结，从零到能独立部署三节点集群并使用 RBD/CephFS/RGW。建议配合 **Kubernetes** 存储章节实践。
