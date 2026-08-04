# 洛谷题面转 NOIP 官方格式 PDF 工具

从洛谷抓取题目，生成符合 **CCF NOIP 官方题面**版式的 PDF，支持双后端：

- **HTML 后端**（默认）：Chromium 打印，无需 LaTeX
- **LaTeX 后端**（`--latex`）：xelatex + minted 排版，格式参考
  [OI-statement-LaTeX](https://github.com/Wallbreaker5th/OI-statement-LaTeX)（WC2021/NOI2021 风格）

输出每题 PDF + 合集 PDF（封面信息表 + 注意事项 + 页码）。

## 安装（首次）

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python download_assets.py   # 下载 KaTeX 字体与思源宋体到 assets/
```

LaTeX 后端需要：

- `xelatex`（MiKTeX 或 TeX Live，含 ctex 宏包）
- **官方同款字体**（与 NOIP 官方 PDF 一致，`ctex` 使用 `fontset=windows`）：
  SimSun（宋体）、SimHei（黑体）、KaiTi、FangSong、Microsoft YaHei、Consolas。
  从 Windows 的 `C:\Windows\Fonts\` 拷贝，或从字体收集仓库下载后放入
  `~/.local/share/fonts/`，然后 `fc-cache -f` + `initexmf --update-fndb`，
  用 `fc-list | grep -i simsun` 验证。
- pygments 已随 requirements 安装（`.venv/bin/pygmentize` 自动加入 PATH）

## 组一场新模拟赛

复制 `contest.example.json` 为 `contest.json`（不入库，已 gitignore），
然后编辑：

```json
{
  "contest": "2026-08-03 模拟赛",
  "date": "2026-08-03",
  "time": "9:00-13:00",
  "duration": "4 小时",
  "problems": [
    { "pid": "P17169", "english": "past" },
    { "pid": "P17170", "english": "future" },
    { "pid": "P17171", "english": "present" },
    { "pid": "P17172", "english": "cause" }
  ],
  "notes": ["自定义注意事项（可省略，有默认值）"]
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `contest` | 比赛名称，显示在封面、页眉和输出目录名 |
| `date` | 比赛日期，封面显示为「2026 年 8 月 3 日」 |
| `time` / `duration` | 比赛时间，封面显示为「09:00 ～ 13:00（4 小时）」 |
| `problems[].pid` | 洛谷题号（仅内部抓取用，不会出现在题面/文件名中） |
| `problems[].english` | 可选，英文名（显示为「题名（english）」，封面可执行文件名）；不填则标题只显示中文名、可执行文件名用 `t1`/`t2` |
| `problems[].type` | 可选，题目类型，默认「传统型」 |
| `notes` | 可选，封面注意事项列表，不填用 NOIP 风格默认值 |

运行：

```bash
.venv/bin/python main.py                    # HTML 后端（默认）
.venv/bin/python main.py --backend latex  # LaTeX 后端
```

也可全部用命令行（不用配置文件）：

```bash
.venv/bin/python main.py --backend latex \
  --contest "2026-08-03 模拟赛" --date 2026-08-03 \
  --time 9:00-13:00 --duration "4 小时" \
  --problems P17169,P17170,P17171,P17172
```

## 输出

```
output/2026-08-03-模拟赛/
  第1题-过去.pdf ... 第4题-因果.pdf   ← 每题一个 PDF
  2026-08-03-模拟赛-题面合集.pdf       ← 封面 + 全部题目
  data/                             ← 样例数据（每组比赛都生成）
    t1/1.in 1.out 2.in 2.out        每个可执行文件名一个目录
    t2/...                          样例按 {n}.in / {n}.out 命名
  package.sh                        一键重新编译 + 打包下发 zip
  tex/                              ← LaTeX 源码（--latex 时生成）
    build.sh                        一键重新编译全部（题数 + 1 个 PDF）
    第1题-过去.tex ...               单题文档（\input 引用题面 body）
    2026-08-03-模拟赛-题面合集.tex    合集文档（封面 + \input 各题面）
    题面/                            题面内容（单题与合集共用）
    statement.cls                    模板（改样式）
    img/                             题面图片
```

**修改题面的工作流**：在 `tex/题面/` 下改对应题目的 `.tex`
（改内容、删列、调格式均可），然后执行：

```bash
cd output/2026-08-03-模拟赛/tex
./build.sh
```

脚本会重新编译全部题目并更新输出目录的 PDF——修改一处，单题和
合集同步生效。`statement.cls` 改全局样式（字体、页眉页脚等）。

## 大表格（超宽）处理

题面表格默认居中于版心内；若某题表格列多导致宽度超过版心
（如 P17172 因果的数据范围表），编辑 `tex/题面/对应题.tex`，
把该表格的外层 `\begin{center}\begin{tblr}{` 改为：

```latex
\begin{center}\makebox[\textwidth][c]{%
\begin{tblr}{
  ...
}
...
\end{tblr}}\end{center}
```

- `\begin{center}` 保留表格上下间距
- `\makebox[\textwidth][c]` 以页面中心为轴——正常宽度时居中于版心，
  超宽时左右对称溢出页边距（而不是只向右侧溢出）

修改后运行 `./build.sh` 重新生成全部 PDF。
（此方法已注释在 `templates/tblr.tex.j2` 模板头部）

## 打包下发

`main.py` 运行完会自动预打包 `<比赛名>-下发.zip`（题面 PDF + `data/` 样例数据）。
修改 `tex/` 源码后，用输出目录下的 `package.sh` 重新编译并打包：

```bash
cd output/<比赛名>/
./package.sh
```

`package.sh` 内部调用 `tex/build.sh`（并行编译，xelatex 日志静默，
只显示进度与失败摘要）。

## 其他选项

| 参数 | 作用 |
|------|------|
| `--backend {html,latex}` | 渲染后端（默认 html） |
| `--output-dir DIR` | 改输出目录（默认 `output/`） |
| `--no-merge` | 不生成合集 PDF |
（HTML 后端中间 HTML 始终输出到 `<比赛名>/html/`；LaTeX 的 tex 源码始终在 `tex/`）
| `--config FILE` | 指定其他配置文件 |

终端输出使用 rich 彩色日志（级别着色、时间戳、失败回溯）。

## 实现说明

```
main.py             CLI 入口：配置合并、抓取编排、双后端分发
model.py            Problem/Contest 数据模型
luogu.py            抓取（assets/extract.js 页面提取脚本）
template.py         HTML 后端（templates/*.html.j2 + style.css.j2）
markdown_latex.py   Markdown→LaTeX 转换器
latex_doc.py        LaTeX 文档组装（templates/*.tex.j2）
compile.py          xelatex 编译
overlay.py          HTML 合集后处理：按题叠加页眉/页码（reportlab）
utils.py            共享格式化工具
tests/              pytest 单元测试（55 个用例）
```

- 数据源：洛谷页面内嵌的 `#lentille-context` JSON，题面为 Markdown 源，
  公式即 LaTeX 源码；HTML 后端复用页面渲染好的 KaTeX。
- 模板用 Jinja2（`templates/`）：改样式/版式直接编辑模板文件，
  不需要动 Python 代码。
- **不暴露洛谷题号**：标题、页眉、封面、文件名均不出现题号；
  英文名用 `problems[].english`（如 `"past"`），未配置时标题只显示中文名，
  封面可执行文件名用 `t1`/`t2` 等编号。
- **防作弊文本**：洛谷嵌入的 `::anti-ai[...]` 标记（隐藏段落）自动删除。
- **节标题映射**：背景/描述/输入输出 →【】格式（黑体）；
  样例 →【样例 N 输入/输出】（minted 行号 + 蓝色边框）；
  说明/提示按 `###` 小标题拆分：【样例 N 解释】独立成节、
  数据范围内容标为【数据范围】。
- **表格**：tabularray 渲染——列间竖线（左右边界无线）、顶/底/表头
  粗线、行间细线；`^` 标记（与上一行同列相同）纵向合并单元格。
- 输入输出默认标准 IO（【输入格式】节注明「从标准输入中读入数据。」）。
- **页眉**：单题用 Chromium headerTemplate（页边距区域，每页重复）；
  HTML 合集因无法按题动态页眉，生成后用 `overlay.py`（reportlab）
  按题分段叠加「比赛名 | 题名」页眉与全局页码（封面无页眉页码）。
- 封面表格列数随题目数自动调整，时限/内存取各测试点的最大值。
- 中间产物（原始 JSON、TeX）在 `.work/`，可随时删除。
- 测试：`pytest tests/` 共 55 个用例；`test_integration.py` 依赖
  `.work/raw_*.json`（先运行过一次抓取），缺失时自动跳过。
