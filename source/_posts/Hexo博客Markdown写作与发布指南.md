---
title: Hexo 博客 Markdown 写作与发布指南
date: 2026-08-12 21:05:00
tags:
  - Hexo
  - Markdown
categories:
  - 博客运维
---

本文介绍如何在本站用 Markdown 写文章，并通过 `git push` 自动发布。

## 新建文章

在博客根目录执行：

```bash
npx hexo new post "文章标题"
```

会在 `source/_posts/` 下生成 Markdown 文件，文件名即 URL 路径的一部分。

## Front Matter 格式

每篇文章开头需要 YAML 元数据：

```yaml
---
title: 文章标题
date: 2026-08-12 21:00:00
tags:
  - 标签一
  - 标签二
categories:
  - 分类名
---
```

正文写在 `---` 之后，支持标准 Markdown。

## 常用 Markdown 语法

### 标题

```markdown
## 二级标题
### 三级标题
```

### 代码块

```python
def hello():
    print("Hello, blog!")
```

### 表格

| 列 A | 列 B |
|------|------|
| 内容 | 内容 |

### 链接与图片

```markdown
[链接文字](https://example.com)
![图片描述](/img/example.png)
```

图片可放在 `source/img/` 目录，引用路径以 `/img/` 开头。

## 本地预览

```bash
npm run server
```

浏览器打开 http://localhost:4000 查看效果，改完即刷新。

## 发布到线上

```bash
git add .
git commit -m "更新文章：文章标题"
git push
```

推送后 GitHub Actions 会自动构建 Hexo，并将静态页面部署到 `gh-pages` 分支。约 1 分钟后线上站点即更新。

## 写作建议

1. **标题清晰**：一句话说明文章价值
2. **分段简短**：每段 3–5 行，便于阅读
3. **代码可运行**：示例尽量完整、可复制
4. **标签统一**：同类文章用相同 tags，方便归档检索

## 本仓库路径速查

| 路径 | 用途 |
|------|------|
| `source/_posts/` | 文章 Markdown |
| `source/img/` | 图片资源 |
| `source/about/` | 关于页 |
| `_config.yml` | 站点全局配置 |
| `_config.fluid.yml` | Fluid 主题配置 |

写好 Markdown、推送到 GitHub，就是本博客的完整发布流程。
