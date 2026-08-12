# cinebee111lagom.github.io

基于 [Hexo](https://hexo.io/) 的个人博客源码，通过 GitHub Actions 自动构建并部署到 GitHub Pages。

## 本地开发

```bash
npm install
npm run server   # 预览 http://localhost:4000
npm run build    # 生成静态文件到 public/
```

## 发布文章

```bash
npx hexo new post "文章标题"
# 编辑 source/_posts/ 下的 Markdown 文件
git add .
git commit -m "更新文章：文章标题"
git push
```

推送后 GitHub Actions 会自动构建，并将结果发布到 `gh-pages` 分支。

## GitHub Pages 设置

仓库 **Settings → Pages** 中，将 **Build and deployment → Branch** 设为 `gh-pages` / `(root)`。
