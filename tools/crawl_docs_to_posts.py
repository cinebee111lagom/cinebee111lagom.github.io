# -*- coding: utf-8 -*-
"""
Batch crawl documentation URLs → Hexo markdown posts.

Usage:
  python tools/crawl_docs_to_posts.py tools/series/etcd_v37.json
  python tools/crawl_docs_to_posts.py tools/series/dragonfly.json tools/series/keda.json tools/series/volcano.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "source" / "_posts"
CACHE = ROOT / ".crawl_cache"
CACHE.mkdir(exist_ok=True)
POSTS.mkdir(parents=True, exist_ok=True)


def cache_path(url: str) -> Path:
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    return CACHE / f"{h}.json"


def fetch(url: str, client: httpx.Client) -> dict:
    cp = cache_path(url)
    if cp.exists():
        return json.loads(cp.read_text(encoding="utf-8"))
    r = client.get(url, follow_redirects=True)
    r.raise_for_status()
    data = {"url": url, "status": r.status_code, "html": r.text}
    cp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.3)
    return data


def extract(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
        tag.decompose()
    main = (
        soup.select_one("article")
        or soup.select_one(".td-content")
        or soup.select_one(".theme-doc-markdown")
        or soup.select_one(".markdown")
        or soup.select_one("main")
        or soup.select_one("#content")
        or soup.select_one(".content")
        or soup.body
    )
    title = ""
    if main:
        h1 = main.find("h1")
        if h1:
            title = h1.get_text(" ", strip=True)
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)
        for sep in ("|", "·", "-"):
            if sep in title:
                title = title.split(sep)[0].strip()
                break
    if main:
        for bad in main.select(
            ".feedback, .td-page-meta, .edit-meta, .pagination-nav, .theme-doc-footer, .hash-link"
        ):
            bad.decompose()
    lines = []
    if not main:
        return {"title": title or url, "markdown": ""}
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre"]):
        name = el.name
        text = el.get_text("\n", strip=True)
        if not text or len(text) < 2:
            continue
        if name.startswith("h"):
            lines.append(("h", int(name[1]), text))
        elif name == "pre":
            lines.append(("code", 0, text[:8000]))
        else:
            if len(text) > 2500:
                text = text[:2500] + "…"
            lines.append(("p", 0, text))
    out, prev = [], None
    for item in lines:
        if item == prev:
            continue
        out.append(item)
        prev = item
    md_parts, chars, max_chars = [], 0, 12000
    for kind, level, text in out:
        if kind == "h" and level == 1:
            continue
        if kind == "h":
            chunk = "\n" + "#" * min(level, 4) + f" {text}\n"
        elif kind == "code":
            chunk = f"\n```\n{text}\n```\n"
        else:
            chunk = f"\n{text}\n"
        if chars + len(chunk) > max_chars:
            md_parts.append("\n\n> （正文已截断，完整内容见官方链接）\n")
            break
        md_parts.append(chunk)
        chars += len(chunk)
    return {"title": title or url, "markdown": "".join(md_parts).strip()}


def slug_from_url(url: str, strip_prefixes: list[str]) -> str:
    path = urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    for pref in strip_prefixes:
        pref_parts = [x for x in pref.strip("/").split("/") if x]
        if parts[: len(pref_parts)] == pref_parts:
            parts = parts[len(pref_parts) :]
            break
    if not parts:
        return "index"
    s = "-".join(parts)
    s = re.sub(r"[^a-zA-Z0-9\-_\u4e00-\u9fff]+", "-", s)
    return s[:100] or "index"


def write_post(cfg: dict, idx: int, url: str, meta: dict) -> Path:
    strip = cfg.get("strip_path_prefixes", [])
    slug = slug_from_url(url, strip)
    prefix = cfg["series_prefix"]
    fn = f"{prefix}-{slug}.md"
    en = meta["title"]
    title = f"{cfg['title_prefix']}{en}"
    date = cfg.get("date", "2026-09-14")
    hh, mm = 9 + idx // 60, idx % 60
    body = meta["markdown"] or "（页面无可提取正文，请直接打开官方链接。）"
    content = f"""---
title: {title}
date: {date} {hh:02d}:{mm:02d}:00
tags:
{chr(10).join('  - ' + t for t in cfg.get('tags', ['文档', '抓取']))}
categories:
  - {cfg['category']}
---

本文由批量爬取官方文档自动生成，保留原文结构要点，便于检索与对照。

**来源**：<{url}>

---

{body}

---

> 完整与最新内容以官方文档为准：[{en}]({url})
"""
    path = POSTS / fn
    path.write_text(content, encoding="utf-8")
    return path


def crawl_series(cfg_path: Path) -> dict:
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    urls = cfg["urls"]
    ok, fail = 0, []
    headers = {
        "User-Agent": "blog-doc-crawler/1.1 (+local hexo; respectful crawl)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    print(f"\n=== {cfg_path.name}: {len(urls)} urls ===")
    with httpx.Client(timeout=45.0, headers=headers) as client:
        for i, url in enumerate(urls):
            try:
                raw = fetch(url, client)
                meta = extract(raw["html"], url)
                path = write_post(cfg, i, url, meta)
                print(f"OK [{i+1}/{len(urls)}] {path.name}")
                ok += 1
            except Exception as e:
                print(f"FAIL {url}: {e}")
                fail.append({"url": url, "error": str(e)})
    report = {"series": cfg_path.name, "ok": ok, "fail": fail, "total": len(urls)}
    (CACHE / f"report_{cfg_path.stem}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        sys.exit(2)
    reports = []
    for arg in argv[1:]:
        p = Path(arg)
        if not p.is_absolute():
            p = ROOT / p
        reports.append(crawl_series(p))
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv)
