---
title: Python 环境搭建：安装与虚拟环境
date: 2026-08-21 09:15:00
tags:
  - Python
  - 环境
categories:
  - Python 新手入门
---

正确的环境配置是写 Python 的第一步。

## 安装 Python

推荐 **Python 3.11 或 3.12**（3.x，不要装 2.x）。

```bash
# Windows：python.org 下载安装，勾选 "Add to PATH"
python --version
pip --version
```

```bash
# macOS
brew install python@3.12

# Linux
sudo apt install python3 python3-pip python3-venv
```

## 虚拟环境（venv）

每个项目独立依赖，避免版本冲突：

```bash
# 创建
python -m venv .venv

# 激活
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# 退出
deactivate
```

激活后命令行前缀显示 `(.venv)`。

## pip 安装包

```bash
pip install requests pandas
pip list
pip freeze > requirements.txt
pip install -r requirements.txt
```

## IDE 选择

| 工具 | 特点 |
|------|------|
| VS Code + Python 插件 | 轻量、免费、推荐 |
| PyCharm Community | 功能全、免费版够用 |
| Cursor | AI 辅助编码 |

## 第一个程序

```python
# hello.py
print("Hello, Python!")
```

```bash
python hello.py
```

## 国内镜像（可选）

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

## 常见问题

| 问题 | 解决 |
|------|------|
| `python` 找不到 | 用 `python3`，或检查 PATH |
| pip 不是内部命令 | `python -m pip install ...` |
| 权限错误 | 用 venv，避免 `sudo pip` |

**养成习惯：新项目先 `python -m venv .venv`**。
