---
title: Flink 版本升级与 Savepoint 迁移
date: 2026-08-18 12:00:00
tags:
  - Flink
  - 升级
  - Savepoint
categories:
  - Flink SRE
---

Flink 升级必须走 **Savepoint**，裸重启会丢状态或无法恢复。

## 升级类型

| 类型 | 风险 | 方式 |
|------|------|------|
| 小版本 1.19.0→1.19.1 | 低 | Savepoint 重启 |
| 大版本 1.17→1.19 | 中 | Savepoint + 兼容性测试 |
| 状态 schema 变更 | 高 | State Migration API |

## 标准升级流程

```bash
# 1. Staging 完整验证
flink stop --savepointPath s3://bucket/savepoints/pre-upgrade <jobId>

# 2. 新集群/新镜像启动
flink run -s s3://bucket/savepoints/pre-upgrade/savepoint-xxx \
  -Dexecution.savepoint.ignore-unclaimed-state=true \
  -c com.example.Job job-1.19.jar

# 3. 验证指标、数据、Checkpoint
# 4. 生产重复，低峰窗口
```

## K8s Operator 升级

```yaml
spec:
  image: flink:1.19.1-custom
  flinkVersion: v1_19
  job:
    upgradeMode: savepoint
    savepointTriggerNonce: 2  # 递增触发
```

## 兼容性注意

- 阅读 **Release Notes** 与 State 兼容性
- Connector 版本同步升级
- `ignore-unclaimed-state` 仅当确认删除了算子时使用

## 回滚

```
保留 upgrade 前 savepoint
回滚 = 旧 jar + 旧 savepoint 启动
```

## 升级前 Checklist

- [ ] Staging savepoint → restore 成功
- [ ] 数据对账（抽样）
- [ ] Checkpoint 正常
- [ ] Kafka offset 语义正确（exactly-once）
- [ ] 回滚 savepoint 路径已记录
- [ ] 变更窗口 + On-Call

## 常见失败

| 错误 | 解决 |
|------|------|
| State schema 不兼容 | State Migration 或清 state 冷启 |
| Serializer 变更 | 自定义 TypeSerializer 迁移 |
| 大版本跳跃 | 逐级升级 |

**无 savepoint 不升级**，是 Flink SRE 铁律。
