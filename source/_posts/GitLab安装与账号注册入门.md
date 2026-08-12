---
title: GitLab 安装与账号注册入门
date: 2026-08-28 09:15:00
tags:
  - GitLab
  - 安装
  - 入门
categories:
  - GitLab 新手入门
---

新手可从 **GitLab.com** 开始，团队私有化再考虑自建。

## GitLab.com 注册

1. 访问 [https://gitlab.com](https://gitlab.com)
2. 注册账号（邮箱或第三方登录）
3. 创建 Group 或 Project
4. 配置 SSH Key：**Preferences → SSH Keys**

```bash
ssh-keygen -t ed25519 -C "you@example.com"
cat ~/.ssh/id_ed25519.pub
# 粘贴到 GitLab SSH Keys
ssh -T git@gitlab.com
```

## 自建 CE 快速体验（Docker）

```bash
docker run -d --hostname gitlab.example.com \
  -p 443:443 -p 80:80 -p 2222:22 \
  --name gitlab \
  --restart always \
  -v gitlab-config:/etc/gitlab \
  -v gitlab-logs:/var/log/gitlab \
  -v gitlab-data:/var/opt/gitlab \
  gitlab/gitlab-ce:latest
```

首次启动需 5~10 分钟，获取初始密码：

```bash
docker exec -it gitlab grep 'Password:' /etc/gitlab/initial_root_password
```

登录 `root`，**立即修改密码**。

## 资源建议（自建）

| 规模 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| 体验 | 2 核 | 4 Gi | 20 Gi |
| 小团队 | 4 核 | 8 Gi | 50 Gi+ |
| 生产 | 8+ 核 | 16+ Gi | SSD 100 Gi+ |

## 首次配置 Checklist

- [ ] 修改 root 密码
- [ ] 创建个人/团队 Group
- [ ] 配置 SSH Key
- [ ] 关闭公开注册（自建生产：`gitlab.rb`）
- [ ] 配置 SMTP 邮件（MR/Issue 通知）

## 反模式

- 生产用默认 root 密码
- 小内存 VM 跑 Omnibus 导致 OOM
- 不备份 `gitlab-data` volume

下一篇：**Git 基础与 GitLab 工作流**。
