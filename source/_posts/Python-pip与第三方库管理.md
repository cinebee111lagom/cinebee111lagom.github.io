---
title: Python pip 与第三方库管理
date: 2026-08-21 11:30:00
tags:
  - Python
  - pip
categories:
  - Python 新手入门
---

第三方库通过 pip 安装，项目管理推荐 `requirements.txt` 或 `pyproject.toml`。

## 常用 pip 命令

```bash
pip install requests
pip install "django>=4.2,<5"
pip uninstall requests
pip show requests
pip list
pip freeze > requirements.txt
pip install -r requirements.txt
pip install --upgrade pip
```

## requirements.txt 示例

```
requests==2.32.3
pandas>=2.0,<3.0
python-dotenv
```

精确版本（`==`）便于复现环境。

## pyproject.toml（现代项目）

```toml
[project]
name = "myapp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.32",
    "pandas>=2.0",
]

[project.optional-dependencies]
dev = ["pytest", "black"]
```

```bash
pip install -e ".[dev]"
```

## 虚拟环境最佳实践

```
每个项目：
  .venv/
  requirements.txt 或 pyproject.toml
  .gitignore 忽略 .venv
```

## 常用第三方库

| 库 | 用途 |
|----|------|
| requests | HTTP 请求 |
| pandas | 数据分析 |
| flask / fastapi | Web |
| pytest | 测试 |
| black | 代码格式化 |
| python-dotenv | 环境变量 |

## 安全注意

- 不要用 `sudo pip install`（污染系统 Python）
- 定期 `pip audit` 检查漏洞（pip 22+）
- 生产锁定版本号

## 国内镜像

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests
```

依赖管理是**项目可复现**的基础。
