---
title: Python 项目结构与打包发布
date: 2026-08-22 09:45:00
tags:
  - Python
  - 项目结构
categories:
  - Python 生产环境
---

清晰的项目结构是可维护、可部署的基础。

## 推荐结构

```
myapp/
├── pyproject.toml          # 或 setup.cfg
├── requirements.txt
├── Dockerfile
├── .env.example            # 不含密钥
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── main.py         # FastAPI app
│       ├── api/
│       │   └── routes/
│       ├── core/
│       │   ├── config.py
│       │   └── logging.py
│       ├── models/
│       └── services/
├── tests/
│   └── test_api.py
└── scripts/
    └── migrate.sh
```

## 配置分离

```python
# src/myapp/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "myapp"
    debug: bool = False
    database_url: str
    redis_url: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

## 入口点

```toml
# pyproject.toml
[project.scripts]
myapp = "myapp.main:cli"
```

```bash
myapp serve   # 或通过 uvicorn myapp.main:app
```

## 打包 wheel

```bash
pip install build
python -m build
# dist/myapp-0.1.0-py3-none-any.whl
pip install dist/myapp-0.1.0-py3-none-any.whl
```

## .gitignore 生产相关

```
.venv/
__pycache__/
*.pyc
.env
dist/
.coverage
```

## 反模式

| 反模式 | 问题 |
|--------|------|
| 单文件 2000 行 | 难测试、难部署 |
| 硬编码配置 | 环境不可切换 |
| 测试不入库 | CI 无法验证 |
| `from xxx import *` | 命名冲突 |

结构清晰 = 部署脚本清晰 = 故障定位快。
