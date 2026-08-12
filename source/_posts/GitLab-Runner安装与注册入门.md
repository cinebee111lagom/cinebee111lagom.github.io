---
title: GitLab Runner 安装与注册入门
date: 2026-08-28 10:30:00
tags:
  - GitLab
  - Runner
  - 入门
categories:
  - GitLab 新手入门
---

**Runner** 是执行 CI Job 的工人，没有 Runner Pipeline 会 **stuck**。

## Runner 类型

| 类型 | 说明 |
|------|------|
| Shared | 实例级，所有项目可用（gitlab.com 提供） |
| Group | 组内项目共享 |
| Project | 单项目专用 |

## 安装 Runner（Linux）

```bash
# 官方仓库安装
curl -L https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh | sudo bash
sudo apt install gitlab-runner

# 或 Docker
docker run -d --name gitlab-runner --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v gitlab-runner-config:/etc/gitlab-runner \
  gitlab/gitlab-runner:latest
```

## 注册 Runner

**Settings → CI/CD → Runners → New project runner**

```bash
sudo gitlab-runner register
# GitLab URL: https://gitlab.com/
# Registration token: （从 UI 复制）
# Description: my-docker-runner
# Tags: docker,linux
# Executor: docker
# Default image: docker:24
```

## Executor 选型

| Executor | 适用 |
|----------|------|
| docker | 最常用，隔离好 |
| shell | 本机直接跑，简单但不隔离 |
| kubernetes | K8s 上动态 Pod |
| docker+machine | 自动扩缩 VM |

## 验证

```yaml
# .gitlab-ci.yml
test-runner:
  tags:
    - docker
  script:
    - echo "Runner OK"
    - uname -a
```

Push 后 Job 应变 **passed**。

## 反模式

- 共享 shell runner 无隔离跑不可信代码
- Runner token 泄露
- 不设 tags 导致 Job 派错 Runner

下一篇：**Pipeline Stage 与 Job 配置**。
