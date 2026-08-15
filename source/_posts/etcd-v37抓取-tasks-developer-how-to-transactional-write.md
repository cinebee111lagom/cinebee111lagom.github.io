---
title: etcd v3.7 抓取：How to make multiple writes in a transaction
date: 2026-09-13 09:21:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/tasks/developer/how-to-transactional-write/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/tasks/developer/how-to-transactional-write/>

---

## Prerequisites

Install
etcd
and
etcdctl
.

etcd

etcdctl

A running
etcd
cluster.

etcd

## Terminology

Here are definitions of some key terms used in the
Example
below.

txn

compare

txn

## Transactions

txn
to process all the requests in one transaction:

txn

```
etcdctl txn --help
```

Transactions in etcd allow you to execute multiple operations atomically, ensuring that either all operations are applied or none are. This is crucial for maintaining data consistency when performing related updates. Learn more about transactions in
the API documentation
.

### Example

Let’s consider a scenario where you want to update a user’s email and phone number in a single transaction. This ensures that both updates are applied together.

#### 0. Variables and Flags used

/users/{<user_id>/email

/users/<user_id>/phone

--interactive

#### 1. Set up initial data

First, create a user with some initial data.

```
etcdctl put /users/12345/email
"old.address@johndoe.com"
etcdctl put /users/12345/phone
"123-456-7890"
```

#### 2. Perform a transaction

Update the user’s email and phone number in a single transaction.

```
etcdctl txn --interactive
compares:
value
(
"/users/12345/email"
)
=
"old.address@johndoe.com"
success requests
(
get, put, delete
)
:
put /users/12345/email
"new.address@johndoe.com"
put /users/12345/phone
"098-765-4321"
failure requests
(
get, put, delete
)
:
get /users/12345/email
```

Compare
: Check if the current email is “
old.address@johndoe.com
”. This ensures the transaction only proceeds if the data is as expected.

Success
: If the comparison is true, update both the email and phone number.

Failure
: If the comparison fails, retrieve the current email to understand why the transaction didn’t proceed.

### Important considerations

Atomicity
: The transaction ensures that both the email and phone number are updated together. If the initial condition (comparison) is not met, neither update is applied.

Consistency
: Using transactions maintains data consistency, especially when dealing with multiple related updates.

Avoid multiple puts on the same key
: Do not put multiple values for the same key within a single transaction, as this can lead to unexpected results. Each key should be updated only once per transaction.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[How to make multiple writes in a transaction](https://etcd.io/docs/v3.7/tasks/developer/how-to-transactional-write/)
