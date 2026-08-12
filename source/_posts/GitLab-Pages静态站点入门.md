---
title: GitLab Pages 静态站点入门
date: 2026-08-28 11:30:00
tags:
  - GitLab
  - Pages
  - 入门
categories:
  - GitLab 新手入门
---

**GitLab Pages** 免费托管静态站点，适合文档、博客、前端 Demo。

## 访问地址

```
https://<username>.gitlab.io/<project-name>/
# 或自定义域名
```

## 最简 .gitlab-ci.yml

```yaml
pages:
  stage: deploy
  script:
    - mkdir -p public
    - echo "<h1>Hello GitLab Pages</h1>" > public/index.html
  artifacts:
    paths:
      - public
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
```

`public/` 目录内容即站点根目录。

## 部署 Hexo / Hugo / Vite

```yaml
# Hexo 示例
pages:
  image: node:20
  script:
    - npm ci
    - npm run build
    - mv public ../public   # Hexo 输出到 public
  artifacts:
    paths:
      - public
  only:
    - main
```

## 自定义域名

**Settings → Pages → New Domain**

DNS 添加 CNAME 指向 GitLab Pages。

## 与 CI 关系

Pages Job 必须：
- 产出 `public/` artifacts
- Job 名称为 `pages`（或 `pages:deploy` 等约定名）

## 反模式

- 分支非 main 期望 Pages 更新
- 构建产物目录不是 `public`
- 大文件进 Pages 仓

适合托管 **项目文档、API 文档、个人主页**。
