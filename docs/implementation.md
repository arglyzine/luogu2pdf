# 实现说明

## 数据流

```
洛谷题目页面
  │  Playwright 无头浏览器（assets/extract.js 页面提取）
  ▼
luogu.py ──┬── 渲染后 HTML（含 KaTeX 样式）→ HTML 后端
           └── #lentille-context 的 Markdown 源（公式即 LaTeX 源码）→ LaTeX 后端
  ▼
model.py（Problem / Contest，双后端共享数据模型）
  ▼
┌──────────────────┬──────────────────────┐
│ HTML 后端         │ LaTeX 后端            │
│ template.py      │ markdown_latex.py    │
│ templates/*.html │  (Markdown→LaTeX)    │
│  + style.css.j2  │ latex_doc.py          │
│ Chromium 打印     │ templates/*.tex      │
│ overlay.py       │ compile.py（xelatex） │
└──────────────────┴──────────────────────┘
```

- **HTML 后端**：复用页面渲染好的 KaTeX 公式与样式，Chromium 打印为 PDF；合集页眉/页码用 reportlab 叠加（`overlay.py`）。
- **LaTeX 后端**：Markdown 源经 `markdown_latex.py` 转 LaTeX，`latex_doc.py` 组装文档，`compile.py` 两遍（必要时三遍）xelatex 编译，样式集中在 `assets/latex/statement.cls`。

## 双后端一致性

改题面处理逻辑（节拆分、表格、格式化）时必须同时考虑两端：

- 共享语义规则抽在 `rules.py`（hint 拆分、样例解释、数据范围分类、`^` 标记），HTML 与 LaTeX 端 import 同一份。
- `assets/extract.js` 是 JS，无法 import，以 `rules.py` 的约定保持一致（行合并仅 `^`）。
- 两端行为有差异时优先改共享层，避免"改一端忘另一端"。

## 模块结构

| 模块 | 职责 |
|------|------|
| `main.py` | CLI 编排：配置校验、抓取、双后端分发 |
| `model.py` | Problem / Contest 数据模型 |
| `luogu.py` | 抓取（Playwright；提取脚本在 `assets/extract.js`） |
| `template.py` | HTML 后端渲染 |
| `markdown_latex.py` | Markdown→LaTeX 转换器（纯函数，测试覆盖最全） |
| `latex_doc.py` | LaTeX 文档组装 |
| `compile.py` | xelatex 编译（页数漂移时自动补第三遍） |
| `overlay.py` | HTML 合集后处理（reportlab 叠页眉/页码） |
| `rules.py` | 双后端共享语义规则 |
| `utils.py` | 共享格式化工具 |

依赖方向：`utils`/`model` → `markdown_latex` → `latex_doc`/`template`/`compile`/`overlay` → `main`。

## 定制入口

- **版式**：`templates/*.j2`（HTML）与 `assets/latex/statement.cls`（LaTeX 全局样式），不要改 Python 字符串。
- **题面渲染行为**：`rules.py`（共享）、`extract.js`（HTML 提取）、`markdown_latex.py`（LaTeX 转换）。
- **示例**：`example/build_example.py` 走与 `main.py` 相同的渲染与编译路径，改样式后重跑即可对照。

## Markdown→LaTeX 转换（markdown-it-py）

解析用 markdown-it-py（`js-default` preset，含表格规则），自写
AST→LaTeX 渲染器（`_render_tokens` 块级 / `_render_inline_children` 行内）。
洛谷方言保留两层：

- **预处理**（喂给解析器之前）：`::anti-ai`、折叠块标记行（3+ 冒号）、
  行内 `::` 标记清理；`$...$`/`$$...$$` 公式占位保护（markdown-it 不解析
  `$`，但公式内容里的 `_`/`*` 会触发强调，必须提前保护）；
  独立 `---` 行换 `___`（段落后紧跟 `---` 会被 CommonMark 解析为
  setext 标题，而洛谷的意图是分隔线）
- **渲染层**：公式占位恢复（`$` 直通 LaTeX 源码）、`^` 表格合并
  （`_table_to_latex`）、blockquote→callout、fence→minted（语言高亮 +
  breaklines 折行）、嵌套列表

踩坑记录（迁移期实测）：

- **公式占位符不能用 NUL**（`\x00`）：markdown-it 的 normalize 会把
  NUL 替换成 U+FFFD，解析后无法恢复——用私用区 `U+E000` 包裹
  （`_protect`/`_restore`）
- **表格 cell 的公式占位跨上下文**：表格公式在主流程解析前已被占位
  保护，cell 渲染必须沿用主流程的 math_tokens 恢复（重新保护会得到
  空列表 → IndexError）——`_table_to_latex(rows, images, math_tokens)`
- **`_collect_until` 返回 close 的索引**（不是 j+1）：调用处赋值后由
  主循环 `i += 1` 自然越过 close，返回 j+1 会再跳过 close 后的第一个
  token（文本丢失）

## 测试

`pytest tests/`（87 个用例）。改 `markdown_latex.py` / `template.py` / `utils.py` / `rules.py` 必须全量跑；`test_integration.py` 依赖 `.work/raw_*.json`（先跑过一次抓取），缺失自动跳过。
