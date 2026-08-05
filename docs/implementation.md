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

## 测试

`pytest tests/`（87 个用例）。改 `markdown_latex.py` / `template.py` / `utils.py` / `rules.py` 必须全量跑；`test_integration.py` 依赖 `.work/raw_*.json`（先跑过一次抓取），缺失自动跳过。
