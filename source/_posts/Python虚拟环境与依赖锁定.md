---
title: Python 虚拟环境与依赖锁定
date: 2026-08-22 09:30:00
tags:
  - Python
  - 依赖
categories:
  - Python 生产环境
---

生产环境必须**可复现**：相同依赖版本在任何机器上行为一致。

## 依赖锁定方式

| 工具 | 文件 | 特点 |
|------|------|------|
| pip | requirements.txt + pip freeze | 简单 |
| pip-tools | requirements.in → .txt | 解析依赖树 |
| Poetry | poetry.lock | 现代项目管理 |
| uv | uv.lock | 极速安装 |

## pip-tools 示例

```bash
pip install pip-tools

# requirements.in
fastapi>=0.110
uvicorn[standard]>=0.27
sqlalchemy>=2.0

pip-compile requirements.in -o requirements.txt
pip-sync requirements.txt
```

## Poetry 示例

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.110.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
```

```bash
poetry lock
poetry install --only main   # 生产只装 main
```

## Docker 中安装

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 或 poetry export -f requirements.txt --without dev
```

## 生产原则

- **锁定所有直接+间接依赖**版本
- CI 中 `pip install -r requirements.txt` 与本地一致
- 定期 `pip audit` / `safety check` / Dependabot
- 不用 `pip install package` 直接改生产

## 私有 PyPI

```bash
pip install -i https://pypi.company.com/simple mypkg
```

## Checklist

- [ ] requirements.txt / poetry.lock 入 Git
- [ ] dev 依赖与 prod 分离
- [ ] CI 漏洞扫描
- [ ] Python 版本在 .python-version 或 Docker 固定

**「在我机器上能跑」的敌人是没有 lock 文件**。
