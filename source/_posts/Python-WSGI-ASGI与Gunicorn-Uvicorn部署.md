---
title: Python WSGI/ASGI 与 Gunicorn/Uvicorn 部署
date: 2026-08-22 10:00:00
tags:
  - Python
  - Gunicorn
  - Uvicorn
categories:
  - Python 生产环境
---

生产**禁止** `python app.py` 直接对外服务，需 WSGI/ASGI 服务器。

## 概念

| 协议 | 服务器 | 框架 |
|------|--------|------|
| WSGI | Gunicorn、uWSGI | Flask、Django |
| ASGI | Uvicorn、Hypercorn | FastAPI |

## Gunicorn（Flask/Django）

```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:8000 "myapp.main:app"
```

```python
# gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
```

## Uvicorn（FastAPI）

```bash
uvicorn myapp.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Gunicorn + Uvicorn Worker（推荐 FastAPI 生产）

```bash
gunicorn myapp.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --timeout 60
```

结合 Gunicorn 进程管理与 Uvicorn 的 ASGI 性能。

## Worker 数量

```
workers = 2 × CPU 核数 + 1        # CPU 密集
workers = CPU 核数                # I/O 密集 async
```

过多 worker → 内存翻倍（每进程独立 Python 解释器）。

## systemd 示例

```ini
[Unit]
Description=MyApp Gunicorn
After=network.target

[Service]
User=app
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/.venv/bin/gunicorn -c gunicorn.conf.py myapp.main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## Nginx 反代

```nginx
upstream myapp {
    server 127.0.0.1:8000;
}
server {
    location / {
        proxy_pass http://myapp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Gunicorn/Uvicorn 管进程，Nginx 管 TLS 和静态资源**。
