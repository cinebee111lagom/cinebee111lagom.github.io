---
title: Python CI/CD 与自动化发布
date: 2026-08-22 12:30:00
tags:
  - Python
  - CI/CD
categories:
  - Python 生产环境
---

CI/CD 保证每次发布经过测试、扫描与可回滚部署。

## GitHub Actions 示例

```yaml
name: CI/CD
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest --cov=src --cov-fail-under=80
      - run: pip-audit -r requirements.txt
      - run: ruff check src/

  build:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: registry.example.com/myapp:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: |
          kubectl set image deployment/myapp-api \
            api=registry.example.com/myapp:${{ github.sha }}
          kubectl rollout status deployment/myapp-api
```

## 流水线阶段

```
lint → test → security scan → build image → deploy staging → deploy prod
```

## 质量门禁

| 门禁 | 工具 |
|------|------|
| 格式/静态 | ruff、black、mypy |
| 测试 | pytest、coverage ≥ 80% |
| 安全 | pip-audit、bandit |
| 镜像 | Trivy scan |

## 发布策略

| 策略 | 说明 |
|------|------|
| 滚动 | K8s 默认 |
| 蓝绿 | 两套环境切换 |
| 金丝雀 | 5% 流量验证 |

## 版本与回滚

```bash
# 镜像 tag 用 git sha，不用 latest
kubectl rollout undo deployment/myapp-api
```

## Checklist

- [ ] PR 必过 CI
- [ ] main 自动部署 staging
- [ ] prod 需 manual approval
- [ ] 回滚 ≤ 5 分钟
- [ ] 发布通知（Slack/飞书）

CI/CD 是**生产稳定性的自动化保险**。
