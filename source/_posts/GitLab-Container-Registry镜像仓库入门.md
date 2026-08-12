---
title: GitLab Container Registry 镜像仓库入门
date: 2026-08-28 12:30:00
tags:
  - GitLab
  - Registry
  - 入门
categories:
  - GitLab 新手入门
---

每个 GitLab Project 自带 **Container Registry**，与 CI 无缝集成。

## 查看镜像

**Deploy → Container Registry**

```
registry.gitlab.com/mygroup/my-api:v1.0.0
registry.gitlab.com/mygroup/my-api:latest
```

## 本地登录推送

```bash
docker login registry.gitlab.com
# Username: GitLab 用户名
# Password: Personal Access Token（read_registry + write_registry）

docker build -t registry.gitlab.com/mygroup/my-api:dev .
docker push registry.gitlab.com/mygroup/my-api:dev
```

## CI 自动推送

CI 中 `$CI_REGISTRY_IMAGE` 等于项目 Registry 路径，配合 `$CI_REGISTRY_USER/PASSWORD` 自动登录。

## 清理策略

**Settings → Packages and registries → Cleanup policies**

```yaml
# 保留最近 10 个 tag，删除 30 天前 untagged
cadence: 1d
older_than: 30d
keep_n: 10
name_regex: .* 
```

避免 Registry 磁盘爆满。

## 与 K8s 拉取

```yaml
# imagePullSecrets
kubectl create secret docker-registry gitlab-reg \
  --docker-server=registry.gitlab.com \
  --docker-username=<user> \
  --docker-password=<token>
```

## 反模式

- 不清理导致 Registry 费用/空间问题
- 生产拉镜像用个人 Token 未轮换
- 镜像无 tag 只有 latest

Registry 是 **GitLab CI → K8s 部署** 链路的中间仓。
