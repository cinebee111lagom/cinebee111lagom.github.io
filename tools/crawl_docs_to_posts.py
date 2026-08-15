# -*- coding: utf-8 -*-
"""
Batch crawl documentation URLs → Hexo markdown posts → ready for git push.
Usage: python tools/crawl_docs_to_posts.py
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
POSTS = ROOT / "source" / "_posts"
CACHE = ROOT / ".crawl_cache"
CACHE.mkdir(exist_ok=True)

CATEGORY = "etcd v3.7 文档导读"
DATE = "2026-09-13"
SERIES_PREFIX = "etcd-v37抓取"

# Full URL list from user (etcd v3.7)
URLS = [
    "https://etcd.io/docs/v3.7/",
    "https://etcd.io/docs/v3.7/quickstart/",
    "https://etcd.io/docs/v3.7/install/",
    "https://etcd.io/docs/v3.7/demo/",
    "https://etcd.io/docs/v3.7/faq/",
    "https://etcd.io/docs/v3.7/feature-gates/",
    "https://etcd.io/docs/v3.7/integrations/",
    "https://etcd.io/docs/v3.7/reporting_bugs/",
    "https://etcd.io/docs/v3.7/tuning/",
    "https://etcd.io/docs/v3.7/tasks/",
    "https://etcd.io/docs/v3.7/tasks/operator/",
    "https://etcd.io/docs/v3.7/tasks/operator/how-to-setup-cluster/",
    "https://etcd.io/docs/v3.7/tasks/operator/how-to-conduct-elections/",
    "https://etcd.io/docs/v3.7/tasks/operator/how-to-check-cluster-status/",
    "https://etcd.io/docs/v3.7/tasks/operator/how-to-save-database/",
    "https://etcd.io/docs/v3.7/tasks/operator/how-to-deal-with-membership/",
    "https://etcd.io/docs/v3.7/tasks/developer/",
    "https://etcd.io/docs/v3.7/tasks/developer/reading-from-etcd/",
    "https://etcd.io/docs/v3.7/tasks/developer/writing-to-etcd/",
    "https://etcd.io/docs/v3.7/tasks/developer/how-to-get-key-by-prefix/",
    "https://etcd.io/docs/v3.7/tasks/developer/how-to-delete-keys/",
    "https://etcd.io/docs/v3.7/tasks/developer/how-to-transactional-write/",
    "https://etcd.io/docs/v3.7/tasks/developer/how-to-watch-keys/",
    "https://etcd.io/docs/v3.7/tasks/developer/how-to-create-lease/",
    "https://etcd.io/docs/v3.7/tasks/developer/how-to-create-locks/",
    "https://etcd.io/docs/v3.7/op-guide/",
    "https://etcd.io/docs/v3.7/op-guide/authentication/",
    "https://etcd.io/docs/v3.7/op-guide/authentication/authentication/",
    "https://etcd.io/docs/v3.7/op-guide/authentication/rbac/",
    "https://etcd.io/docs/v3.7/op-guide/configuration/",
    "https://etcd.io/docs/v3.7/op-guide/security/",
    "https://etcd.io/docs/v3.7/op-guide/clustering/",
    "https://etcd.io/docs/v3.7/op-guide/kubernetes/",
    "https://etcd.io/docs/v3.7/op-guide/container/",
    "https://etcd.io/docs/v3.7/op-guide/failures/",
    "https://etcd.io/docs/v3.7/op-guide/recovery/",
    "https://etcd.io/docs/v3.7/op-guide/gateway/",
    "https://etcd.io/docs/v3.7/op-guide/grpc_proxy/",
    "https://etcd.io/docs/v3.7/op-guide/hardware/",
    "https://etcd.io/docs/v3.7/op-guide/maintenance/",
    "https://etcd.io/docs/v3.7/op-guide/monitoring/",
    "https://etcd.io/docs/v3.7/op-guide/performance/",
    "https://etcd.io/docs/v3.7/op-guide/runtime-reconf-design/",
    "https://etcd.io/docs/v3.7/op-guide/runtime-configuration/",
    "https://etcd.io/docs/v3.7/op-guide/supported-platform/",
    "https://etcd.io/docs/v3.7/op-guide/versioning/",
    "https://etcd.io/docs/v3.7/op-guide/data_corruption/",
    "https://etcd.io/docs/v3.7/dev-guide/",
    "https://etcd.io/docs/v3.7/dev-guide/discovery_protocol/",
    "https://etcd.io/docs/v3.7/dev-guide/local_cluster/",
    "https://etcd.io/docs/v3.7/dev-guide/interacting_v3/",
    "https://etcd.io/docs/v3.7/dev-guide/api_grpc_gateway/",
    "https://etcd.io/docs/v3.7/dev-guide/grpc_naming/",
    "https://etcd.io/docs/v3.7/dev-guide/golang_embed_pkg/",
    "https://etcd.io/docs/v3.7/dev-guide/limit/",
    "https://etcd.io/docs/v3.7/dev-guide/features/",
    "https://etcd.io/docs/v3.7/dev-guide/api_reference_v3/",
    "https://etcd.io/docs/v3.7/dev-guide/api_concurrency_reference_v3/",
    "https://etcd.io/docs/v3.7/learning/",
    "https://etcd.io/docs/v3.7/learning/data_model/",
    "https://etcd.io/docs/v3.7/learning/design-client/",
    "https://etcd.io/docs/v3.7/learning/design-learner/",
    "https://etcd.io/docs/v3.7/learning/design-auth-v3/",
    "https://etcd.io/docs/v3.7/learning/api/",
    "https://etcd.io/docs/v3.7/learning/persistent-storage-files/",
    "https://etcd.io/docs/v3.7/learning/api_guarantees/",
    "https://etcd.io/docs/v3.7/learning/why/",
    "https://etcd.io/docs/v3.7/learning/glossary/",
    "https://etcd.io/docs/v3.7/upgrades/",
    "https://etcd.io/docs/v3.7/upgrades/upgrading-etcd/",
    "https://etcd.io/docs/v3.7/upgrades/upgrade_3_0/",
    "https://etcd.io/docs/v3.7/upgrades/upgrade_3_1/",
    "https://etcd.io/docs/v3.7/upgrades/upgrade_3_2/",
    "https://etcd.io/docs/v3.7/upgrades/upgrade_3_3/",
    "https://etcd.io/docs/v3.7/upgrades/upgrade_3_4/",
    "https://etcd.io/docs/v3.7/upgrades/upgrade_3_5/",
    "https://etcd.io/docs/v3.7/upgrades/upgrade_3_6/",
    "https://etcd.io/docs/v3.7/upgrades/upgrade_3_7/",
    "https://etcd.io/docs/v3.7/downgrades/",
    "https://etcd.io/docs/v3.7/downgrades/downgrading-etcd/",
    "https://etcd.io/docs/v3.7/downgrades/downgrade_3_5/",
    "https://etcd.io/docs/v3.7/downgrades/downgrade_3_6/",
    "https://etcd.io/docs/v3.7/downgrades/downgrade_3_7/",
    "https://etcd.io/docs/v3.7/benchmarks/",
    "https://etcd.io/docs/v3.7/benchmarks/etcd-2-1-0-alpha-benchmarks/",
    "https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-benchmarks/",
    "https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-rc-benchmarks/",
    "https://etcd.io/docs/v3.7/benchmarks/etcd-2-2-0-rc-memory-benchmarks/",
    "https://etcd.io/docs/v3.7/benchmarks/etcd-3-demo-benchmarks/",
    "https://etcd.io/docs/v3.7/benchmarks/etcd-3-watch-memory-benchmark/",
    "https://etcd.io/docs/v3.7/benchmarks/etcd-storage-memory-benchmark/",
    "https://etcd.io/docs/v3.7/metrics/",
    "https://etcd.io/docs/v3.7/triage/",
    "https://etcd.io/docs/v3.7/triage/issues/",
    "https://etcd.io/docs/v3.7/triage/PRs/",
    "https://etcd.io/docs/v3.7/dev-internal/discovery_protocol/",
    "https://etcd.io/docs/v3.7/dev-internal/logging/",
    "https://etcd.io/docs/v3.7/dev-internal/modules/",
]


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
    time.sleep(0.35)
    return data


def extract(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    # etcd docs: main content often in article / td-content / main
    main = (
        soup.select_one("article")
        or soup.select_one(".td-content")
        or soup.select_one("main")
        or soup.select_one("#content")
        or soup.body
    )
    title = ""
    h1 = main.find("h1") if main else None
    if h1:
        title = h1.get_text(" ", strip=True)
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True).split("|")[0].strip()
    # remove feedback widgets
    if main:
        for bad in main.select(".feedback, .td-page-meta, .edit-meta"):
            bad.decompose()
    lines = []
    if not main:
        return {"title": title or url, "sections": [], "text": ""}
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre", "code", "td", "th"]):
        name = el.name
        text = el.get_text("\n", strip=True)
        if not text or len(text) < 2:
            continue
        if name in ("h1", "h2", "h3", "h4"):
            level = int(name[1])
            lines.append(("h", level, text))
        elif name == "pre" or (name == "code" and el.parent and el.parent.name == "pre"):
            if name == "code" and el.parent.name == "pre":
                continue
            lines.append(("code", 0, text))
        elif name in ("td", "th"):
            continue  # tables handled loosely via p/li; skip cell noise
        else:
            if len(text) > 2000:
                text = text[:2000] + "…"
            lines.append(("p", 0, text))
    # dedupe consecutive identical
    out = []
    prev = None
    for item in lines:
        if item == prev:
            continue
        out.append(item)
        prev = item
    # build markdown body (cap size)
    md_parts = []
    chars = 0
    max_chars = 12000
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
    return {"title": title or url, "markdown": "".join(md_parts).strip(), "url": url}


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p and p != "docs" and p != "v3.7"]
    if not parts:
        return "index"
    s = "-".join(parts)
    s = re.sub(r"[^a-zA-Z0-9\-_]+", "-", s)
    return s[:80]


def cn_title(en_title: str, slug: str) -> str:
    base = en_title.replace(" | etcd", "").strip()
    return f"etcd v3.7 抓取：{base}"


def write_post(idx: int, meta: dict) -> Path:
    slug = slug_from_url(meta["url"])
    fn = f"{SERIES_PREFIX}-{slug}.md"
    title = cn_title(meta["title"], slug)
    hh = 9 + idx // 60
    mm = idx % 60
    body = meta["markdown"] or "（页面无可提取正文，请直接打开官方链接。）"
    # light Chinese framing
    content = f"""---
title: {title}
date: {DATE} {hh:02d}:{mm:02d}:00
tags:
  - etcd
  - 抓取
  - 文档
categories:
  - {CATEGORY}
---

本文由批量爬取 [etcd v3.7 文档]({meta['url']}) 自动生成，保留原文结构要点，便于检索与对照。

**来源**：<{meta['url']}>

---

{body}

---

> 完整与最新内容以官方文档为准：[{meta['title']}]({meta['url']})
"""
    path = POSTS / fn
    path.write_text(content, encoding="utf-8")
    return path


def main():
    POSTS.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, []
    results = []
    headers = {
        "User-Agent": "blog-doc-crawler/1.0 (+local hexo; respectful crawl)",
        "Accept": "text/html,application/xhtml+xml",
    }
    with httpx.Client(timeout=45.0, headers=headers) as client:
        for i, url in enumerate(URLS):
            try:
                raw = fetch(url, client)
                meta = extract(raw["html"], url)
                meta["url"] = url
                results.append(meta)
                path = write_post(i, meta)
                print(f"OK [{i+1}/{len(URLS)}] {path.name} <- {url}")
                ok += 1
            except Exception as e:
                print(f"FAIL {url}: {e}")
                fail.append({"url": url, "error": str(e)})
    report = {"ok": ok, "fail": fail, "total": len(URLS)}
    (CACHE / "last_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
