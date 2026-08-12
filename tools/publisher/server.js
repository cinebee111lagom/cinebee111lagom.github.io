const express = require('express');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3456;
const BLOG_ROOT = path.resolve(__dirname, '../../');
const POSTS_DIR = path.join(BLOG_ROOT, 'source', '_posts');

app.use(express.json({ limit: '2mb' }));
app.use(express.static(path.join(__dirname, 'public')));

function safeFilename(name) {
  return name.replace(/[<>:"/\\|?*]/g, '').trim();
}

function resolvePostPath(filename) {
  const name = safeFilename(filename);
  if (!name.endsWith('.md')) return null;
  const postsRoot = path.resolve(POSTS_DIR);
  const full = path.resolve(postsRoot, name);
  if (!full.startsWith(postsRoot + path.sep)) return null;
  return full;
}

function listPosts() {
  if (!fs.existsSync(POSTS_DIR)) return [];
  return fs
    .readdirSync(POSTS_DIR)
    .filter((f) => f.endsWith('.md'))
    .map((filename) => {
      const full = path.join(POSTS_DIR, filename);
      const raw = fs.readFileSync(full, 'utf8');
      const titleMatch = raw.match(/^title:\s*(.+)$/m);
      const dateMatch = raw.match(/^date:\s*(.+)$/m);
      return {
        filename,
        title: titleMatch ? titleMatch[1].trim().replace(/^['"]|['"]$/g, '') : filename,
        date: dateMatch ? dateMatch[1].trim() : '',
        size: fs.statSync(full).size,
      };
    })
    .sort((a, b) => (b.date > a.date ? 1 : -1));
}

function parseFrontMatter(raw) {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!match) {
    return { meta: {}, body: raw };
  }
  const meta = {};
  const lines = match[1].split(/\r?\n/);
  let currentKey = null;
  for (const line of lines) {
    const keyVal = line.match(/^(\w+):\s*(.*)$/);
    if (keyVal) {
      currentKey = keyVal[1];
      const val = keyVal[2].trim();
      if (val) {
        meta[currentKey] = val.replace(/^['"]|['"]$/g, '');
      } else {
        meta[currentKey] = [];
      }
    } else if (currentKey && line.match(/^\s+-\s+/)) {
      if (!Array.isArray(meta[currentKey])) meta[currentKey] = [];
      meta[currentKey].push(line.replace(/^\s+-\s+/, '').trim());
    }
  }
  return { meta, body: match[2] };
}

function buildFrontMatter({ title, date, tags, categories, math }) {
  const tagItems = (tags || []).filter(Boolean);
  const catItems = (categories || []).filter(Boolean);

  let yaml = `---\n`;
  yaml += `title: ${title}\n`;
  yaml += `date: ${date}\n`;
  if (math) {
    yaml += `math: true\n`;
  }
  yaml += `tags:\n`;
  if (tagItems.length) {
    yaml += tagItems.map((t) => `  - ${t}`).join('\n') + '\n';
  }
  if (catItems.length) {
    yaml += `categories:\n`;
    yaml += catItems.map((c) => `  - ${c}`).join('\n') + '\n';
  }
  yaml += `---\n`;
  return yaml;
}

function formatDate() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function detectMath(body) {
  return /\$\$[\s\S]+?\$\$|\$[^$\n]+?\$/.test(body || '');
}

function runGit(cmd) {
  return execSync(cmd, { cwd: BLOG_ROOT, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
}

app.get('/api/posts', (_req, res) => {
  res.json({ posts: listPosts() });
});

app.get('/api/posts/:filename', (req, res) => {
  const filename = safeFilename(req.params.filename);
  const full = path.join(POSTS_DIR, filename);
  if (!fs.existsSync(full)) {
    return res.status(404).json({ error: '文章不存在' });
  }
  const raw = fs.readFileSync(full, 'utf8');
  const { meta, body } = parseFrontMatter(raw);
  res.json({ filename, meta, body, raw });
});

app.post('/api/posts', (req, res) => {
  const { title, tags, categories, body } = req.body;
  if (!title || !body) {
    return res.status(400).json({ error: '标题和正文不能为空' });
  }
  const filename = safeFilename(req.body.filename || title) + '.md';
  const full = path.join(POSTS_DIR, filename);
  if (fs.existsSync(full)) {
    return res.status(409).json({ error: '文件已存在，请换标题或指定文件名' });
  }
  const date = req.body.date || formatDate();
  const content = buildFrontMatter({ title, date, tags, categories, math: req.body.math ?? detectMath(body) }) + '\n' + body.trim() + '\n';
  fs.writeFileSync(full, content, 'utf8');
  res.json({ ok: true, filename });
});

app.put('/api/posts/:filename', (req, res) => {
  const filename = safeFilename(req.params.filename);
  const full = path.join(POSTS_DIR, filename);
  if (!fs.existsSync(full)) {
    return res.status(404).json({ error: '文章不存在' });
  }
  const { title, date, tags, categories, body } = req.body;
  if (!title || !body) {
    return res.status(400).json({ error: '标题和正文不能为空' });
  }
  const content =
    buildFrontMatter({
      title,
      date: date || formatDate(),
      tags,
      categories,
      math: req.body.math ?? detectMath(body),
    }) +
    '\n' +
    body.trim() +
    '\n';
  fs.writeFileSync(full, content, 'utf8');
  res.json({ ok: true, filename });
});

app.delete('/api/posts/:filename', (req, res) => {
  try {
    const full = resolvePostPath(req.params.filename);
    if (!full || !fs.existsSync(full)) {
      return res.status(404).json({ error: '文章不存在' });
    }
    const filename = path.basename(full);
    fs.unlinkSync(full);
    res.json({ ok: true, filename });
  } catch (err) {
    res.status(500).json({ error: '删除失败', detail: err.message });
  }
});

app.post('/api/publish', (req, res) => {
  const message = (req.body.message || '更新博客文章').trim();
  try {
    runGit('git add -A -- source/_posts/');
    const status = runGit('git status --porcelain source/_posts/');
    if (!status.trim()) {
      return res.json({ ok: true, skipped: true, message: '没有需要发布的文章变更' });
    }
    runGit(`git commit -m "${message.replace(/"/g, '\\"')}"`);
    runGit('git push origin main');
    res.json({ ok: true, message: '已推送到 GitHub，Actions 将自动部署' });
  } catch (err) {
    const stderr = err.stderr || err.message;
    res.status(500).json({ error: '发布失败', detail: stderr });
  }
});

app.listen(PORT, () => {
  console.log(`\n  博客写作台: http://localhost:${PORT}\n  文章目录: ${POSTS_DIR}\n`);
});
