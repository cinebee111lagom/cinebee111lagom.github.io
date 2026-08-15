---
title: etcd 底层：Learner 只读成员
date: 2026-09-12 09:15:00
tags:
  - etcd
  - Learner
categories:
  - etcd v3.7 底层细节
---

Learner：先加入为非投票成员同步数据，再提升为投票成员，降低直接 `member add` 对多数派的冲击。

## 价值

- 扩容时减少“未追上就投票”的风险
- 变更窗口更可控

提升前确认同步进度；提升后按奇数投票成员规划（3/5）。

> 延伸阅读：[Design learner](https://etcd.io/docs/v3.7/learning/design-learner/)

