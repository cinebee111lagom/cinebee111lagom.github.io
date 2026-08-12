---
title: GitLab Docker 镜像构建与推送入门
date: 2026-08-28 11:15:00
tags:
  - GitLab
  - Docker
  - 入门
categories:
  - GitLab 新手入门
---

GitLab CI 最常见的 Job 之一：**build 镜像 → push 到 Registry**。

## 使用内置 Registry

Registry 地址：`registry.gitlab.com/<group>/<project>`

```yaml
variables:
  IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

build-and-push:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $IMAGE .
    - docker push $IMAGE
    - docker tag $IMAGE $CI_REGISTRY_IMAGE:latest
    - docker push $CI_REGISTRY_IMAGE:latest
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

## Dockerfile 示例

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

## Kaniko（无 Docker socket）

```yaml
build:
  image:
    name: gcr.io/kaniko-project/executor:debug
    entrypoint: [""]
  script:
    - /kaniko/executor
        --context $CI_PROJECT_DIR
        --dockerfile Dockerfile
        --destination $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

适合 K8s Runner，无需 privileged。

## 多阶段 Pipeline

```
lint → build image → scan → push → deploy（更新 GitOps 仓 tag）
```

## 反模式

- dind 无 privileged 导致失败
- latest 唯一 tag 无法回滚
- 镜像无 layer 缓存导致极慢

下一篇：**GitLab Pages**。
