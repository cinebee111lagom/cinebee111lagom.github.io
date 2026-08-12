---
title: Python 环境变量与配置管理
date: 2026-08-22 11:00:00
tags:
  - Python
  - 配置
categories:
  - Python 生产环境
---

生产配置遵循 **12-Factor**：配置存环境变量，代码与配置分离。

## pydantic-settings（推荐）

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_env: str = "production"
    debug: bool = False
    database_url: str
    redis_url: str = ""
    secret_key: str
    log_level: str = "INFO"

settings = Settings()
```

```bash
# .env.example（入 Git，无真实值）
DATABASE_URL=postgresql://user:pass@localhost:5432/db
SECRET_KEY=change-me
LOG_LEVEL=INFO
```

## 环境区分

| 环境 | 方式 |
|------|------|
| dev | .env 本地 |
| staging | K8s ConfigMap |
| prod | K8s Secret + 外部 Vault |

## 密钥管理

```python
# 不要
API_KEY = "sk-hardcoded-xxx"

# 要
API_KEY = settings.api_key  # 来自 os.environ
```

| 工具 | 场景 |
|------|------|
| K8s Secret | 基础 |
| AWS Secrets Manager | 云环境 |
| HashiCorp Vault | 企业 |
| SOPS | Git 加密配置 |

## 配置验证

```python
@validator("database_url")
def validate_db(cls, v):
    if not v.startswith("postgresql"):
        raise ValueError("需要 PostgreSQL")
    return v
```

启动时 fail fast，避免半配置运行。

## 动态配置（可选）

```python
# 功能开关从 Redis/配置中心拉取
if feature_flags.get("new_checkout"):
    ...
```

## Checklist

- [ ] 无密钥入 Git
- [ ] .env.example 文档化
- [ ] 生产 debug=False
- [ ] 敏感项走 Secret 管理
- [ ] 配置变更可审计

**配置错误是生产事故常见根因**，启动校验必不可少。
