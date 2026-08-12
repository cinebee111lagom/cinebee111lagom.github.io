---
title: MinIO 安装与单机部署入门
date: 2026-09-01 09:30:00
tags:
  - MinIO
  - 安装
  - 入门
categories:
  - MinIO 新手入门
---

单机模式适合 **开发、POC、小流量**，一条命令即可启动。

## 二进制安装（Linux）

```bash
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/

wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc && sudo mv mc /usr/local/bin/
```

## 启动服务

```bash
export MINIO_ROOT_USER=admin
export MINIO_ROOT_PASSWORD='YourStrongPass123!'

mkdir -p /data/minio
minio server /data/minio --console-address ":9001"
```

| 端口 | 用途 |
|------|------|
| 9000 | S3 API |
| 9001 | Web Console |

## Docker 方式

```bash
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD='YourStrongPass123!' \
  -v /data/minio:/data \
  minio/minio server /data --console-address ":9001"
```

## systemd 服务（生产单机）

```ini
[Unit]
Description=MinIO
After=network.target

[Service]
User=minio
Environment="MINIO_ROOT_USER=admin"
Environment="MINIO_ROOT_PASSWORD=xxx"
ExecStart=/usr/local/bin/minio server /data/minio --console-address ":9001"
Restart=always

[Install]
WantedBy=multi-user.target
```

## 验收

```bash
curl http://localhost:9000/minio/health/live
# 浏览器 http://<ip>:9001 登录 Console
```

## 反模式

- 默认弱密码
- 数据目录在系统盘且无备份
- 生产长期用单机无分布式

下一篇：**分布式集群**。
