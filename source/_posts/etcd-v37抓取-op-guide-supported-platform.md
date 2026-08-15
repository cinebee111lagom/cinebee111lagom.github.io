---
title: etcd v3.7 抓取：Supported platforms
date: 2026-09-13 09:44:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - etcd v3.7 文档导读
---

本文由批量爬取 [etcd v3.7 文档](https://etcd.io/docs/v3.7/op-guide/supported-platform/) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://etcd.io/docs/v3.7/op-guide/supported-platform/>

---

## Support tiers

etcd runs on different platforms, but the guarantees it provides depends on a
platform’s support tier:

Tier 1
: fully supported by
etcd maintainers
; etcd is guaranteed to
pass all tests including functional and robustness tests.

Tier 2
: etcd is guaranteed to pass integration and end-to-end tests but
not necessarily functional or robustness tests.

Tier 3
: etcd is guaranteed to build, may be lightly tested (or not), and
so it should be considered
unstable
.

## Current support

The following table lists currently supported platforms and their corresponding
etcd support tier:

Unlisted platforms are unsupported.

## Supporting a new platform

Want to contribute to etcd as the “official” maintainer of a new platform? In
addition to committing to support the platform, you must setup etcd continuous
integration (CI) satisfying the following requirements, depending on the support
tier:

For an example of setting up tier-2 CI for ARM64, see
etcd PR #12928
.

## Unsupported platforms

To avoid inadvertently running an etcd server on an unsupported platform, etcd
prints a warning message and exits immediately unless the environment variable
ETCD_UNSUPPORTED_ARCH
is set to the target architecture.

ETCD_UNSUPPORTED_ARCH

etcd has
known issues
on 32-bit systems due to a bug in the Go runtime.
For more information see the
Go issue #599
and the
atomic package
bug note
.

## Feedback

Was this page helpful?

Glad to hear it! Please
tell us how we can improve
.

Sorry to hear that. Please
tell us how we can improve
.

---

> 完整与最新内容以官方文档为准：[Supported platforms](https://etcd.io/docs/v3.7/op-guide/supported-platform/)
