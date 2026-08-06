
() => {
  const res = { pid: '', title: '', timeLimit: '', memoryLimit: '',
                sections: {}, samples: [] };

  const titleH2 = document.querySelector('h2.title');
  if (titleH2) {
    const parts = titleH2.textContent.trim().split(/\s+/);
    res.pid = parts[0] || '';
    res.title = parts.slice(1).join(' ') || res.pid;
  }

  for (const f of document.querySelectorAll('header .stat .field')) {
    const name = f.querySelector('.name');
    const value = f.querySelector('.value');
    if (name && value) {
      const k = name.textContent.trim();
      const v = value.textContent.trim();
      if (k === '时间限制') res.timeLimit = v;
      if (k === '内存限制') res.memoryLimit = v;
    }
  }

  // 删除防作弊隐藏文本（洛谷出题人嵌入的 .invisible 段落，对选手不可见）
  for (const el of document.querySelectorAll('.lfe-marked .invisible')) {
    el.remove();
  }
  for (const el of document.querySelectorAll('.lfe-marked *')) {
    const st = el.getAttribute('style') || '';
    if (/display\s*:\s*none|visibility\s*:\s*hidden/i.test(st)) el.remove();
  }
  // 去掉 HTML 注释节点（Vue 注释与出题人注释）
  const walker = document.createTreeWalker(document.querySelector('main'), NodeFilter.SHOW_COMMENT);
  const comments = [];
  while (walker.nextNode()) comments.push(walker.currentNode);
  for (const c of comments) c.remove();

  // :::warning 提示块 → 普通 div（去掉 summary「警告」与折叠箭头，内容保留）
  for (const det of document.querySelectorAll('.lfe-marked details.warning')) {
    const s = det.querySelector('summary');
    if (s) s.remove();
    const div = document.createElement('div');
    div.className = 'warning';
    div.innerHTML = det.innerHTML;
    det.replaceWith(div);
  }

  // 数据范围表格：仅 ^ 标记处合并（^ 表示与上一行同列相同，纵向 rowspan）
  for (const table of document.querySelectorAll('.lfe-marked table, .cute-table table')) {
    const trs = [...table.querySelectorAll('tr')];
    const data = trs.map(tr => [...tr.querySelectorAll('td, th')].map(c => c.innerHTML));
    const ncols = Math.max(0, ...data.map(r => r.length));
    // 记录 ^ 位置，再展开（继承上方最近非 ^ 值）
    const caret = data.map(row => row.map(cell => (cell || '').trim() === '^'));
    for (let r = 1; r < data.length; r++) {
      for (let c = 0; c < data[r].length; c++) {
        if (caret[r][c]) {
          for (let rr = r - 1; rr >= 0; rr--) {
            if (!caret[rr][c]) { data[r][c] = data[rr][c]; break; }
          }
        }
      }
    }
    // 仅 ^ 连续段与其来源行合并（表头行不参与）
    const spans = data.map(r => r.map(() => 1));
    const covered = data.map(r => r.map(() => false));
    for (let c = 0; c < ncols; c++) {
      let r = 1;
      while (r < data.length) {
        if (caret[r][c]) {
          let end = r;
          while (end + 1 < data.length && caret[end + 1][c]) end++;
          spans[r - 1][c] = end - (r - 1) + 1;
          for (let k = r; k <= end; k++) covered[k][c] = true;
          r = end + 1;
        } else {
          r++;
        }
      }
    }
    for (let r = 0; r < trs.length; r++) {
      const cells = [...trs[r].querySelectorAll('td, th')];
      cells.forEach((cell, idx) => {
        if (covered[r][idx]) cell.remove();
        else if (spans[r][idx] > 1) cell.rowSpan = spans[r][idx];
      });
    }
  }

  // 题面图片：补全懒加载 src，移除懒加载属性，确保打印时全部加载
  for (const img of document.querySelectorAll('.lfe-marked img')) {
    if (!img.getAttribute('src')) {
      const lazy = img.getAttribute('data-src') || img.getAttribute('data-original')
                 || img.getAttribute('data-lazy-src') || img.getAttribute('data-url');
      if (lazy) img.setAttribute('src', lazy);
    }
    img.removeAttribute('loading');
    img.removeAttribute('data-src');
    img.removeAttribute('data-original');
    img.removeAttribute('data-lazy-src');
    img.removeAttribute('data-url');
  }

  const main = document.querySelector('main');
  if (main) {
    const h2s = [...main.querySelectorAll('h2')];
    for (let i = 0; i < h2s.length; i++) {
      const h = h2s[i];
      const name = h.textContent.trim();
      const blocks = [];
      let nxt = h.nextElementSibling;
      while (nxt && nxt.tagName !== 'H2') { blocks.push(nxt); nxt = nxt.nextElementSibling; }

      if (name === '输入输出样例') {
        for (const b of blocks) {
          for (const sb of b.querySelectorAll('.io-sample-block')) {
            const cap = sb.querySelector('b');
            const pre = sb.querySelector('pre');
            if (!cap || !pre) continue;
            const m = cap.textContent.trim().match(/^(输入|输出)\s*#?(\d+)/);
            if (m) res.samples.push({ kind: m[1], n: parseInt(m[2], 10), text: pre.textContent });
          }
        }
      } else {
        // 保留整块容器 outerHTML（含 data-v 属性）
        let html = '';
        for (const b of blocks) {
          const wrap = b.classList.contains('lfe-marked-wrap')
              ? b : b.querySelector('.lfe-marked-wrap');
          html += (wrap || b).outerHTML;
        }
        if (html) res.sections[name] = html;
      }
    }
  }

  // Markdown 源数据（用于 LaTeX 后端）：公式为 LaTeX 源码，防作弊为 ::anti-ai[]
  // contenu = 当前语言（中文站）题面；content = 原始语言（外文题原文）
  const lc = document.getElementById('lentille-context');
  if (lc) {
    try {
      const j = JSON.parse(lc.textContent);
      const pr = j.data.problem;
      res.md = {
        name: pr.name || '',
        content: pr.contenu || pr.content || {},
        samples: pr.samples || [],
        limits: pr.limits || {}
      };
    } catch (e) {}
  }
  return res;
}
