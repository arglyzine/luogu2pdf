\ProvidesClass{statement}[Statement Class for Olympiad in Informatics]
\NeedsTeXFormat{LaTeX2e}

\LoadClass[12pt,fontset=windows]{ctexart}

\RequirePackage{geometry}
\geometry{bottom=20mm,top=25mm,left=27mm,right=27mm}

\RequirePackage{titling}

\newcommand\SubtitleContent{}
\newcommand\subtitle[1]{\renewcommand\SubtitleContent{#1}}
\pretitle{\vspace*{-20mm}\begin{center}\LARGE\bfseries}
\posttitle{\par\mdseries\LARGE\SubtitleContent\end{center}\vskip 0.5em}

\RequirePackage{fontspec}
\setmonofont{Consolas}
% 官方题面的 sans 是黑体（SimHei），ctex windows fontset 默认用微软雅黑，覆盖
\setCJKsansfont{SimHei}

\RequirePackage{titlesec}
% 表格线宽：竖线/细线更清晰（\Xhline 按此倍数加粗）
\setlength{\arrayrulewidth}{0.7pt}
\newcommand{\Attention}{\begingroup\titleformat{\subsection}{\bf}{}{0pt}{\hspace{0.5em}}\subsection[注意事项（请仔细阅读）]{【注意事项（请仔细阅读）】}\endgroup}
% 题目标题：中文粗体=黑体（SimHei），西文粗体=LMRoman12-Bold，与官方一致
\titleformat{\section}{\Large\bfseries}{}{0pt}{\centering\label{sec:\thesection}}
% 节标题：中文黑体（\heiti 只切换 CJK，西文保持正文衬线），字号大一号
\titleformat{\subsection}{\heiti\large}{}{0.5em}{}
\titleformat{\subsubsection}{\heiti\large}{}{0.5em}{}

\RequirePackage{enumitem}
\setenumerate[1]{itemsep=0pt,partopsep=0pt,parsep=\parskip,topsep=5pt}
\setitemize[1]{itemsep=0pt,partopsep=0pt,parsep=\parskip,topsep=5pt}
% 嵌套列表标签：第二层用白色空心圆点（◦），第三层延续默认
\renewcommand{\labelitemii}{$\circ$}


\RequirePackage{fancyhdr}
\RequirePackage{totpages}
\RequirePackage{color}
\pagestyle{fancy}
% 页眉右侧只显示题名，不带节编号
\renewcommand{\sectionmark}[1]{\markboth{#1}{#1}}
\fancyhead[L]{\footnotesize \@title}
\fancyhead[R]{\footnotesize\MakeLowercase{\fancyplain{}{\leftmark}}}
\fancyfoot[C]{\footnotesize 第 \thepage 页 \hspace{2em} 共 { \color{blue} \pageref*{TotPages}} 页}


\RequirePackage{lineno}
\RequirePackage{tikz}
\RequirePackage{tcolorbox}
\RequirePackage{lineno}
\RequirePackage{fancyvrb}
\renewcommand{\theFancyVerbLine}{\ttfamily\textcolor{gray}{\footnotesize\arabic{FancyVerbLine}}}
\tcbuselibrary{most}

\usepackage{etoolbox}
% 样例框（minted 3.8 后端自带跨页能力，tcolorbox 包裹分帧）：
% frame hidden 关闭 tcolorbox 的 frame 绘制——包括断点处的
% 淡化装饰线（front 底/last 顶）与分帧灰填充，全部边框改由
% overlay 逐帧绘制，断点处完全无线，只有左右线连续贯穿：
%   first   顶线 + 左右线（顶部两角圆角，底部无线）
%   middle  左右线（直角，上下无线）
%   last    左右线 + 底线（底部两角圆角，顶部无线）
%   unbroken 完整四边框（四角圆角）
% segmentation at break=false：不画分割线（对消除断点线无效，
% frame hidden 才是），但去掉断点处保留的分割空间（默认 ~11pt），
% 内容更紧凑、跨页样例前后页数更稳定
% boxrule=0pt：frame hidden 只关闭绘制，boxrule 仍参与每帧
% 高度计算（默认 0.4pt × 上下两条 × 多帧会跨页漂移，合集
% 12→13 页实测）
% 注：overlay unbroken 需要 skin=enhanced（first/middle/last 不需要）
\BeforeBeginEnvironment{minted}{
    \begin{tcolorbox}[
        skin=enhanced,
        breakable,
        frame hidden,
        boxrule=0pt,
        segmentation at break=false,
        arc=1mm,
        colback=white,
        parbox=false,
        left=2mm,
        overlay unbroken={
            \draw[blue, line width=0.5pt, rounded corners=1mm] (frame.south west)--(frame.north west)--(frame.north east)--(frame.south east)--cycle;
        },
        overlay first={
            \draw[blue, line width=0.5pt, rounded corners=1mm] (frame.south west)--(frame.north west)--(frame.north east)--(frame.south east);
        },
        overlay middle={
            \draw[blue, line width=0.5pt] (frame.north west)--(frame.south west);
            \draw[blue, line width=0.5pt] ([xshift=-0.5pt]frame.north east)--([xshift=-0.5pt]frame.south east);
        },
        overlay last={
            \draw[blue, line width=0.5pt, rounded corners=1mm] (frame.north west)--(frame.south west)--(frame.south east)--(frame.north east);
        },
        ]}
\AfterEndEnvironment{minted}{\end{tcolorbox}}

% 引用/说明块（admonition 样式：左侧粗线 + 浅灰底 + 直角，
% 参考 tex.stackexchange.com/q/687578）
\newtcolorbox{callout}[1][]{breakable, sharp corners, parbox=false,
  boxrule=0mm, leftrule=2mm, boxsep=0mm, arc=0mm, outer arc=0mm,
  colback=gray!8, colframe=black, #1}


\RequirePackage{xeCJKfntef}
\newcommand\stress[1]{\textbf{\CJKunderdot{#1}}}
\newcommand\filename[1]{\textbf{\textit{#1}}}
\newcommand\ttstring[1]{\texttt{\uline{#1}}}
\newcommand\englishname[1]{\texorpdfstring{\textrm{\textmd{\MakeLowercase{#1}}}}{#1}}
