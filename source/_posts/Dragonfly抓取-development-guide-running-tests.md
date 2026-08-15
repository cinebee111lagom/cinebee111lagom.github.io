---
title: Dragonfly 抓取：Running Tests
date: 2026-09-14 10:08:00
tags:
  - Dragonfly
  - 抓取
  - 文档
categories:
  - Dragonfly 抓取导读
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<https://d7y.io/docs/next/development-guide/running-tests/>

---

This document describes how to run unit tests and E2E tests.

## Prerequisites

## Unit tests

Unit tests is in the project directory.

### Running unit tests

```
make test
```

### Running uint tests with coverage reports

```
make test-coverage
```

## E2E tests

E2E tests is in
dragonfly/test/e2e
path.

### Running E2E tests

```
make e2e-test
```

### Running E2E tests with coverage reports

```
make e2e-test-coverage
```

### Clean E2E tests environment

```
make clean-e2e-test
```

---

> 完整与最新内容以官方文档为准：[Running Tests](https://d7y.io/docs/next/development-guide/running-tests/)
