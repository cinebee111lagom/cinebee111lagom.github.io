---
title: Python 生产安全实践
date: 2026-08-22 11:45:00
tags:
  - Python
  - 安全
categories:
  - Python 生产环境
---

Python 生产安全覆盖依赖漏洞、密钥、输入校验与最小权限。

## 依赖漏洞扫描

```bash
pip install pip-audit
pip-audit -r requirements.txt

# CI 中
pip-audit --strict --requirement requirements.txt
```

配合 Dependabot/Renovate 自动 PR 升级。

## 密钥管理

```python
# 禁止
SECRET = "hardcoded-key"

# 正确
import os
SECRET = os.environ["SECRET_KEY"]
```

- 密钥轮换策略
- 日志脱敏：不输出 Authorization header

## 输入校验

```python
from pydantic import BaseModel, Field, EmailStr

class CreateUser(BaseModel):
    email: EmailStr
    age: int = Field(ge=0, le=150)
    name: str = Field(min_length=1, max_length=100)
```

FastAPI/Pydantic 自动校验，拒绝非法输入。

## SQL 注入防护

```python
# 禁止字符串拼接
f"SELECT * FROM users WHERE id = {user_id}"

# 使用 ORM 或参数化
session.execute(select(User).where(User.id == user_id))
```

## HTTPS 与 Header

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from secure import SecureHeaders

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["api.example.com"])
# SecureHeaders 设置 HSTS、X-Frame-Options 等
```

## 容器安全

- 非 root 用户运行
- 只读 root filesystem（可选）
- 最小基础镜像
- 定期扫描镜像 Trivy/Snyk

## 限流

```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.get("/api/data")
@limiter.limit("100/minute")
async def get_data():
    ...
```

## Checklist

- [ ] pip-audit CI 通过
- [ ] 无硬编码密钥
- [ ] HTTPS 全站
- [ ] CORS 白名单
- [ ] 容器非 root
- [ ] 敏感 API 鉴权

安全是**左移**到 CI 和代码审查的。
