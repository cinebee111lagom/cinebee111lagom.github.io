---
title: Python 脚本自动化入门
date: 2026-08-21 13:00:00
tags:
  - Python
  - 自动化
categories:
  - Python 新手入门
---

Python 是运维和办公自动化的首选语言，几行代码替代重复劳动。

## 批量重命名

```python
from pathlib import Path

for i, f in enumerate(Path("photos").glob("*.jpg"), 1):
    f.rename(f.parent / f"vacation_{i:03d}{f.suffix}")
```

## 定时任务（schedule）

```bash
pip install schedule
```

```python
import schedule
import time

def job():
    print("备份执行...")

schedule.every().day.at("02:00").do(job)
schedule.every(30).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

生产环境用 **cron**（Linux）或 **Task Scheduler**（Windows）调用脚本更可靠。

## 发送邮件

```python
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("报告内容", "plain", "utf-8")
msg["Subject"] = "日报"
msg["From"] = "bot@example.com"
msg["To"] = "user@example.com"

with smtplib.SMTP("smtp.example.com", 587) as s:
    s.starttls()
    s.login("bot@example.com", "password")
    s.send_message(msg)
```

## 监控目录变化

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        print(f"新文件: {event.src_path}")

# observer = Observer() ...
```

## 调用系统命令

```python
import subprocess

result = subprocess.run(
    ["git", "status"],
    capture_output=True,
    text=True,
    check=True,
)
print(result.stdout)
```

## 自动化脚本模板

```python
#!/usr/bin/env python3
"""日志清理脚本"""
import argparse
import logging
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    # 业务逻辑...

if __name__ == "__main__":
    main()
```

自动化脚本：**小步验证 → 加日志 → 加异常处理 → 上定时任务**。
