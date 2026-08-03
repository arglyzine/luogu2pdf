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
\BeforeBeginEnvironment{minted}{
    \begin{tcolorbox}[
        colframe=blue,
        breakable=true,
        colback = white,
        boxrule = 0.5pt,
        left=2mm,
        ]}
\AfterEndEnvironment{minted}{\end{tcolorbox}}

\newenvironment{example}
{
    \ttfamily
    \begin{tcolorbox}[
        colframe=blue,
        breakable=true,
        left=0.3125in,
        colback = white,
        boxrule = 0.5pt,
        left=5mm,
        ]\begingroup\linenumbers}
{
    \endgroup\end{tcolorbox}
}


\RequirePackage{xeCJKfntef}
\newcommand\stress[1]{\textbf{\CJKunderdot{#1}}}
\newcommand\filename[1]{\textbf{\textit{#1}}}
\newcommand\ttstring[1]{\texttt{\uline{#1}}}
\newcommand\englishname[1]{\texorpdfstring{\textrm{\MakeLowercase{#1}}}{#1}}
