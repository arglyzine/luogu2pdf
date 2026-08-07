# TODO

## Markdown 解析器迁移（markdown-it-py）——规划中，未开始

**现状问题**：`markdown_latex.py` 手写 markdown 解析（`_split_blocks` 分块 +
`_inline` 行内），不断补 corner case（引用块 `>` 后无空格、`::::` 折叠块、
`_x_` 下划线斜体等）——重复造轮子，手写正则永远在追 corner case。

**方案**：用 markdown-it-py 解析 CommonMark → AST，自写 AST→LaTeX 渲染器。

- 解析归标准库：blockquote、嵌套列表、围栏代码、强调、链接、图片
- 洛谷方言保留两层：
  - 预处理：`::anti-ai`、`::::info[标题]` 折叠块标记行清理（简单正则，已有）
  - 渲染层：`$...$` 公式直通（markdown 不解析 `$`，天然安全）、
    `^` 表格合并、callout、tblr 表格
- 渲染层复用现有：`_table_to_latex` / `_list_to_tex` / callout / 样例框，
  输入从"自分的块"换成"AST 节点"
- 验收：`tests/test_latex.py` 全绿（现有用例是迁移安全网）
- 依赖：markdown-it-py（纯 Python，无二进制）

**触发时机**：再次遇到手写解析的 corner case 时优先迁移，而非继续补丁。
