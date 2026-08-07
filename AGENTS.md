# AGENTS.md

洛谷题面转 NOIP 官方格式 PDF 工具。抓取洛谷题目，生成官方版式题面
（封面/页眉/【】节标题/样例框/数据范围表），支持 HTML 与 LaTeX 双后端。

## 环境与依赖

- Python 虚拟环境：`.venv/`（`python3 -m venv .venv`，依赖见 `requirements.txt`）
- 运行命令一律用 `.venv/bin/python`（如 `.venv/bin/python main.py`）
- 测试：`.venv/bin/pytest tests/`（55 个用例，`pytest.ini` 配置了 pythonpath）
- LaTeX 后端需要：`xelatex`（MiKTeX）、`pygmentize`（已随 .venv 安装，
  LaTeX 编译时需把 `.venv/bin` 加进 PATH）、系统中文字体
  （SimSun/SimHei/Consolas，见下方「字体」）
- HTML 后端需要：Playwright Chromium（`.venv/bin/playwright install chromium`）

## 目录约定

| 路径 | 用途 | 是否入库 |
|------|------|---------|
| `.venv/` | Python 环境 | 否（.gitignore） |
| `.work/` | 临时文件：raw_*.json（抓取缓存）、problem_*.html、编译目录 | 否 |
| `output/` | LaTeX 后端输出（PDF + tex/ 源码目录） | 否 |
| `output-html/` | HTML 后端输出 | 否 |
| `assets/fonts/`、`assets/katex/` | 下载的字体/公式资源（`download_assets.py` 重建） | 否 |
| `assets/extract.js` | 洛谷页面提取脚本（独立 JS 文件，勿内嵌回 Python） | 是 |
| `assets/latex/statement.cls` | LaTeX 模板（样式修改在这） | 是 |
| `templates/` | Jinja2 模板（HTML 与 LaTeX 的版式都在这） | 是 |
| `reference/` | 官方参考 PDF（如 noip-2024.pdf） | 否 |

## 常用命令

```bash
.venv/bin/python main.py                  # HTML 后端（默认）
.venv/bin/python main.py --latex          # LaTeX 后端
.venv/bin/python main.py --problems P1000,P1001 --contest "名称" --date 2026-08-03
.venv/bin/pytest tests/                   # 全部测试
bash output/<比赛名>/tex/build.sh         # 修改 tex/ 源码后一键重编译
.venv/bin/python download_assets.py       # 重建字体/KaTeX 资源
```

## 架构（模块职责）

```
main.py              CLI 编排：配置校验、抓取、双后端分发、HTML 合集分段
model.py             Problem/Contest dataclass（两个后端共享的数据模型）
luogu.py             抓取（Playwright；提取脚本在 assets/extract.js）
template.py          HTML 后端渲染（templates/*.html.j2 + style.css.j2）
rules.py             双后端共享语义规则（hint 拆分/样例解释/数据范围/^ 标记）
markdown_latex.py    Markdown→LaTeX 转换器（纯函数，测试覆盖最全）
latex_doc.py         LaTeX 文档组装（templates/*.tex.j2）
compile.py           xelatex 两遍编译
overlay.py           HTML 合集后处理：按题叠加页眉/全局页码（reportlab）
utils.py             共享格式化工具（日期/时限/内存/文件名）
```

依赖方向（无循环）：`utils`/`model` → `markdown_latex` → `latex_doc`/
`template`/`compile`/`overlay` → `main`。

## 关键行为与约定

- **双后端一致性**：改题面处理逻辑（合并、节拆分、格式化）必须同时考虑
  HTML（`extract.js` + `template.py` + CSS）与 LaTeX（`markdown_latex.py`）。
- **不暴露洛谷题号**：标题/页眉/封面/文件名用 `english` 或 `t{index}`。
- **数据流**：`luogu.py` 从页面 DOM 取渲染后 HTML（HTML 后端用），从
  `#lentille-context` 取 Markdown 源（LaTeX 后端用，公式即 LaTeX 源码）。
- **lentille 结构**：`#lentille-context` 是 `<script type="application/json">`，
  `JSON.parse(textContent)` 后取 `data.problem`：
  - `contenu`：**当前语言题面**（中文站为中文翻译，含 `locale` 字段；
    外文题如 USACO 有翻译）。`content` 是**原始语言**（英文原文）——
    读 contenu，不要读 content（P16574 案例）
  - `content.contenu` 的 key：`name/background/description/formatI/formatO/hint/locale`
  - `samples`：`[["输入","输出"], ...]`；`limits`：`{"time":[ms...],"memory":[KB...]}`
  - `attachments`：`[{id, filename, size, uploadTime, downloadLink}]`，
    `downloadLink` 为相对路径，拼 `https://www.luogu.com.cn` 下载
- **附件登录态**：附件下载 API（downloadAttachment）需登录（匿名 302/
  无 cookie 403 UserNotLoggedIn）。登录态来自项目根 `.luogu_cookies.json`
  （`__client_id`/`_uid`，gitignore，example 模板入库），luogu.py 注入
  Playwright context；无配置时附件下载失败仅 warning，不影响抓取。
  下载后的附件：`.work/attachments/<pid>/`（缓存）→
  `output/<比赛名>/data/<exec_name>/`（导出，与样例同目录）→ 下发 zip；题面
  末尾生成【附件】节（LaTeX `\filename` 加粗斜体 / HTML `<b><i>`）。
  抓取后 main 会提示：题面含代码块（PDF 内不便复制，提醒配置附件）、
  附件为 *.in/.out/.ans 数据文件（提醒配置 english 使目录名与题对应）。
  - 页面 DOM 的 `h2.title`、`.problem` 渲染区（sections）与附件卡片
    不在 JSON 里，仍从 DOM 提取（extract.js）
- **模板改版式**：改 `templates/*.j2`（HTML）或 `assets/latex/statement.cls`
  （LaTeX 全局样式），不要改 Python 字符串。
- **测试**：改 `markdown_latex.py`/`template.py`/`utils.py` 必须跑
  `pytest tests/`；`tests/test_integration.py` 依赖 `.work/raw_*.json`
  （先跑过一次抓取），缺失自动跳过。

## Git 工作流与提交约定

- **分支**：GitHub Flow——`main` 永远可发布；功能在 `feat/*` 分支开发，
  合并用 `--no-ff`（保留功能边界），合并后删除分支。
- **提交信息**：Conventional Commits——`feat:`/`fix:`/`docs:`/`test:`/
  `chore:`（必要时 `!`/`BREAKING CHANGE:`）。
- **版本**：SemVer——`feat`→minor、`fix`→patch、`breaking`→major
  （0.x 阶段 minor 递增功能）；发布用 annotated tag + `gh release`
  （notes 用文件）。
- **提交纪律**：每次提交单一逻辑——验收反馈的修复也拆开提交
  （如 `fix: 附件节换行`、`fix: 样例不折行`），不要攒横切功能的大
  commit（横切后合并前重组必须拆 hunk，代价高）。
- **合并前重组**：规划 commit 分组 → 逐文件检查归属；交叉文件用
  「中间版本法」（checkout 起点版 + 脚本提取插入），不要用
  `git add -p` 管道（hunk 顺序脆弱）；`amend` 只碰 HEAD，多 commit
  调整用 `rebase -i`；历史无保留价值时直接 squash 成一个大 commit。

## 已知坑（改动前必读）

- **breaklines 膨胀样例框 padding**：fvextra 折行行
  `\parbox[t]{\noindent\strut...\strut}` 的首尾 strut 让框上下
  padding 增加 ~12pt（与行数无关）；样例框（text 数据）不要开
  breaklines，只给代码块开（`sample.tex.j2` 的 `wrap` 参数）。
- **嵌入 LaTeX 的字符串必须 `_escape_special`**：english/exec_name/
  附件名/文件名含下划线（如 `ex_dream`）会触发 `Missing $` →
  `-halt-on-error` 中止 → afterlastpage 钩子不跑 → minted batch
  不执行 → 全部样例变 `<MINTED>` 占位（连环故障）。
- **markdown 解析已迁移 markdown-it-py**（2026-08-07，见
  `docs/implementation.md` 的「Markdown→LaTeX 转换」章节）：解析归
  标准库，洛谷方言在预处理/渲染层处理。再遇渲染 corner case 时优先
  在预处理层或渲染层解决，不要回退手写解析器。

- **tabularray 与 tabularx 冲突**：同一文档加载两者时，`>{\centering\arraybackslash}X`
  列格式报错；封面表格用 tabularx + `\multicolumn`，题面表格用 tabularray。
- **tabularray 的 `\SetCell[c=N]` 列合并在当前版本报错**（行合并 `[r=N]` 正常）；
  需跨列时用 `\multicolumn`（tabularx）。
- **reportlab 不支持 OTF PostScript outlines**：overlay 用系统
  DroidSansFallback（TrueType），且它是纯中文字体——数字/英文需
  Helvetica 混合绘制（`overlay._draw_mixed`）。
- **Chromium 打印丢弃 <1px border**：HTML 表格细线用 `1px`（不要用 0.7pt）。
- **贴版心右缘的边框打印时被舍入丢弃**（样例框右线曾丢失）：右侧需内缩
  （`margin-right: 1px`）。
- **Chromium 打印的 `text-emphasis` 会把点渲染成占位字符**：强调文字用
  `text-emphasis` 正常（字旁点），不要改成逐字 span 方案。
- **Jinja2 注释是 `{# ... #}`**，不是 Django 的 `{% comment %}`；LaTeX
  模板里 `{%`（如 `\makebox{%`）会被当标签，需避开。
- **hint 拆分节（数据范围/样例解释/特别鸣谢）是片段**，无 `.lfe-marked`
  包装：HTML 端需手动补 `<div class="lfe-marked">` 才有正文缩进样式；
  表格选择器要覆盖 `.cute-table table`。
- **fitz 会把中文标题拆成单字 span**：定位 h1 标题（合集分段）时需
  拼接同页大字文本再匹配，字号阈值 16.5pt（h1=17.22，节标题=14.35）。
- **LaTeX 编译**：必须 `-shell-escape`（minted 需要 pygments），PATH 含
  `.venv/bin`；`TEXINPUTS` 指向 `assets/latex/`（statement.cls）。
- **字体**：LaTeX 封面用 ctex `fontset=windows`（SimSun/SimHei/KaiTi/
  FangSong/微软雅黑需装入 `~/.local/share/fonts` 并 `initexmf --update-fndb`）。

## PDF 渲染验证技巧（像素级确认）

文本层提取（`get_text`）不可靠：着重号点会插入字符间、KaTeX/公式 span 拆分、
行序乱——验证边框/线/位置/合并等视觉元素时，用**渲染 + 像素分析**，
不要依赖肉眼或 AI 看图（本模型不支持图片输入）：

```python
import fitz
from PIL import Image
import numpy as np

page = fitz.open("xxx.pdf")[n]
# 高 DPI 渲染目标区域（clip 用 pt 坐标），300dpi 下 1px ≈ 0.24pt
page.get_pixmap(dpi=300, clip=fitz.Rect(x0, y0, x1, y1)).save("t.png")
img = np.array(Image.open("t.png").convert("RGB"))

# 1) 找指定颜色的竖线（如样例框蓝 #2E74B5）：
#    像素 x → 页面 pt：pt = x * 72 / dpi + clip.x0
blue = (abs(img[:, :, 0].astype(int) - 0x2E) < 40) \
     & (abs(img[:, :, 1].astype(int) - 0x74) < 40) \
     & (abs(img[:, :, 2].astype(int) - 0xB5) < 40)
cols = [x for x in range(img.shape[1]) if blue.sum(axis=0)[x] > img.shape[0] * 0.3]

# 2) 找横线：按行统计暗像素（y 同理换算 pt）
dark_rows = (np.array(Image.open("t.png").convert("L")) < 160).sum(axis=1)

# 3) 验证居中：元素左/右边缘的 pt 坐标，中心应 ≈ 页面中心（A4 = 297.5pt）
# 4) 验证合并单元格/边框缺失：比对左右边缘像素列是否存在
```

常用判定：
- 边框四边：分别检测左/右列、顶/底行的连续暗/彩色像素
- 表格线存在性：横线（`dark_rows` 的宽行带）与竖线（列带）的数量和位置
- 元素是否贴边被裁：`search_for("文字")` 得到 x 坐标后换算，与预期版心边界比较

- **注意**：0.4-0.7pt 细线在 150dpi 下灰度浅、阈值易漏报——用 300dpi +
  宽松阈值（<160~<200）或按颜色精确匹配。
- **边框可能渲染为填充矩形而非描边**：tcolorbox 等边框在 PDF 里常是
  `fill=(0,0,1)` 的填充路径（`color` 为 None）——检测时 fill 与 color
  都要查；竖线/边框的判定阈值按元素实际高度（如样例框仅 25pt）取，
  不要用裁剪区域高度比例，否则小元素会被漏报。
