let currentFilename = null;

const $ = (id) => document.getElementById(id);

function splitCsv(str) {
  return str
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function setStatus(text, type = '') {
  const el = $('status');
  el.textContent = text;
  el.className = 'status' + (type ? ` ${type}` : '');
}

async function loadPosts() {
  const res = await fetch('/api/posts');
  const data = await res.json();
  const list = $('post-list');
  list.innerHTML = '';
  data.posts.forEach((post) => {
    const li = document.createElement('li');
    li.dataset.filename = post.filename;
    li.innerHTML = `<div>${post.title}</div><div class="meta">${post.date || post.filename}</div>`;
    li.addEventListener('click', () => openPost(post.filename, li));
    list.appendChild(li);
  });
}

async function openPost(filename, liEl) {
  const res = await fetch(`/api/posts/${encodeURIComponent(filename)}`);
  if (!res.ok) {
    setStatus('加载失败', 'error');
    return;
  }
  const data = await res.json();
  currentFilename = data.filename;
  $('title').value = data.meta.title || '';
  $('tags').value = Array.isArray(data.meta.tags) ? data.meta.tags.join(', ') : '';
  $('categories').value = Array.isArray(data.meta.categories) ? data.meta.categories.join(', ') : '';
  $('body').value = data.body.trim();
  $('commit-msg').value = `更新文章：${data.meta.title || filename}`;

  document.querySelectorAll('.post-list li').forEach((el) => el.classList.remove('active'));
  if (liEl) liEl.classList.add('active');
  setStatus(`已加载：${filename}`);
}

function newPost() {
  currentFilename = null;
  $('title').value = '';
  $('tags').value = '';
  $('categories').value = '';
  $('body').value = '';
  $('commit-msg').value = '';
  document.querySelectorAll('.post-list li').forEach((el) => el.classList.remove('active'));
  setStatus('新建文章 — 填写后点击保存');
}

async function savePost(silent = false) {
  const payload = {
    title: $('title').value.trim(),
    tags: splitCsv($('tags').value),
    categories: splitCsv($('categories').value),
    body: $('body').value,
  };
  if (!payload.title || !payload.body) {
    if (!silent) setStatus('标题和正文不能为空', 'error');
    return false;
  }

  let res;
  if (currentFilename) {
    res = await fetch(`/api/posts/${encodeURIComponent(currentFilename)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } else {
    res = await fetch('/api/posts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  }

  const data = await res.json();
  if (!res.ok) {
    if (!silent) setStatus(data.error || '保存失败', 'error');
    return false;
  }
  currentFilename = data.filename;
  $('commit-msg').value = `更新文章：${payload.title}`;
  if (!silent) {
    setStatus(`已保存：${data.filename}`, 'ok');
    await loadPosts();
  }
  return true;
}

async function publish() {
  const hasDraft = $('title').value.trim() && $('body').value.trim();
  if (hasDraft) {
    setStatus('正在保存…');
    const saved = await savePost(true);
    if (!saved) {
      setStatus('请先填写标题和正文', 'error');
      return;
    }
    await loadPosts();
  }

  const msg = $('commit-msg').value.trim() || `更新文章：${$('title').value.trim()}`;
  setStatus('正在发布…');
  const res = await fetch('/api/publish', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg }),
  });
  const data = await res.json();
  if (!res.ok) {
    setStatus((data.error || '发布失败') + (data.detail ? `\n${data.detail}` : ''), 'error');
    return;
  }
  if (data.skipped) {
    setStatus('没有变更需要发布：文章已与线上一致，或请先修改内容后再点发布', 'ok');
    return;
  }
  setStatus(data.message || '发布成功', 'ok');
}

$('btn-new').addEventListener('click', newPost);
$('btn-save').addEventListener('click', savePost);
$('btn-publish').addEventListener('click', publish);

loadPosts();
