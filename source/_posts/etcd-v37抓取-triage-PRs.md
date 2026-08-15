---
title: etcd v3.7 抓取：PR management
date: 2026-09-13 10:34:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/triage/PRs/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/triage/PRs/>

---

## Purpose

Speed up PR management.

The
etcd
PRs are listed at
https://github.com/etcd-io/etcd/pulls
A PR can have various labels, milestone, reviewer etc. The detailed list of labels can be found at
https://github.com/kubernetes/kubernetes/labels

etcd

Following are few example searches on PR for convenience:

Open PRS for milestone etcd-v3.4

PRs under investigation

## Scope

These guidelines serves as a primary document for managing PRs in
etcd
. Everyone is welcome to help manage PRs but the work and responsibilities discussed in this document is created with
etcd
maintainers and active contributors in mind.

etcd

## Handle inactive PRs

Poke PR owner if review comments are not addressed in 15 days. If PR owner does not reply in 90 days, update the PR with a new commit if possible. If not, inactive PR should be closed after 180 days.

## Poke reviewer if needed

Reviewers are responsive in a timely fashion, but considering everyone is busy, give them some time after requesting review if quick response is not provided. If response is not provided in 10 days, feel free to contact them via adding a comment in the PR or sending an email or message on the Slack.

## Verify important labels are in place

Make sure that appropriate reviewers are added to the PR. Also, make sure that a milestone is identified. If any of these or other important labels are missing, add them. If a correct label cannot be decided, leave a comment for the maintainers to do so as needed.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[PR management](https://etcd.io/docs/v3.7/triage/PRs/)
