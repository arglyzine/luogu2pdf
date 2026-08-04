"""双后端共享的题面语义规则。

HTML（template.py / assets/extract.js）与 LaTeX（markdown_latex.py /
latex_doc.py）对题面结构的理解必须一致——hint 拆分、样例解释识别、
数据范围/提示判断、^ 表格标记等语义集中在此，两端 import 同一份，
避免行为漂移（改一端忘另一端的静默 bug）。

注意：assets/extract.js 是页面提取阶段的独立 JS（无法 import 本模块），
其 ^ 合并逻辑与下方 CARET 文档约定保持一致。
"""

import re

# 洛谷 markdown 小标题（hint 拆分依据）：1-4 级 #，允许行首缩进
HINT_HEADING_RE = re.compile(r"^\s*#{1,4}\s+(.+?)\s*$")

# 样例解释节标题识别（容错公式标记，如「样例 $1$ 解释」）
SAMPLE_EXPLAIN_RE = re.compile(r"样例\s*\$?\s*(\d+)\s*\$?\s*解释")

# 「数据范围」节关键词（正文中出现即视为数据范围节）
DATARANGE_RE = re.compile(r"数据范围|对于\s*100\s*%\s*的数据|测试点")

# ^ 表格标记：洛谷数据范围表中表示「与上一行同列相同」
# （LaTeX 端合并单元格；HTML 端在 extract.js 中做 rowspan，语义相同）
CARET = "^"


def classify_hint(text):
    """判断说明/提示节标题：含数据范围关键词 → 数据范围，否则提示。

    输入可为渲染后 HTML 或 Markdown 源（统一去标签后判断）。
    """
    plain = re.sub(r"<[^>]+>", " ", text)
    return "数据范围" if DATARANGE_RE.search(plain) else "提示"


def sample_explain_number(title):
    """识别样例解释节标题，返回样例编号或 None（非样例解释节）。"""
    m = SAMPLE_EXPLAIN_RE.search(title)
    return m.group(1) if m else None
