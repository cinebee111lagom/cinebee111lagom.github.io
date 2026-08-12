---
title: Python Docker 容器化部署
date: 2026-08-22 10:30:00
tags:
  - Python
  - Docker
categories:
  - Python 生产环境
---

Docker 保证开发到生产环境一致，是 Python 服务部署的标准方式。

## 多阶段 Dockerfile

```dockerfile
# 构建阶段
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir pip-tools
COPY requirements.txt .
RUN pip wheel --no-cache-dir -r requirements.txt -w /wheels

# 运行阶段
FROM python:3.12-slim
WORKDIR /app
RUN useradd -m -u 1000 appuser
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY src/ ./src/
USER appuser
EXPOSE 8000
CMD ["gunicorn", "myapp.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "2", "-b", "0.0.0.0:8000"]
```

## 要点

| 项 | 建议 |
|----|------|
| 基础镜像 | slim 或 distroless |
| 用户 | 非 root（appuser） |
| 层缓存 | 先 COPY requirements 再代码 |
| .dockerignore | 排除 .venv、tests、.git |

## .dockerignore

```
.venv
__pycache__
.git
.env
tests/
*.md
```

## docker-compose 生产片段

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

## 环境变量

```yaml
environment:
  DATABASE_URL: postgresql://user:pass@postgres:5432/db
  LOG_LEVEL: INFO
```

密钥用 Docker secrets 或外部 Secret 管理。

## 常见问题

| 问题 | 解决 |
|------|------|
| 镜像过大 | 多阶段、slim 基础镜像 |
| 权限错误 | USER 非 root |
| 时区 | `ENV TZ=Asia/Shanghai` |

容器化后下一步通常是 **K8s 编排**。
