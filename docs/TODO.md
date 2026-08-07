# TODO

## ~~Markdown 解析器迁移（markdown-it-py）~~ 已完成（2026-08-07）

解析改用 markdown-it-py（js-default preset，含表格规则），AST→LaTeX
渲染器在 `markdown_latex.py`（实现细节与踩坑记录见该文件注释）。
