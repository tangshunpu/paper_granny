% ============================================================
% ModernColorful.cls — 美观多彩的技术文档模板
% 编译方式: XeLaTeX
% 用法: \documentclass{ModernColorful}
% ============================================================
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ModernColorful}[2026/03/16 Modern Colorful Report Template]

% 基于 article
\LoadClass[11pt,a4paper]{article}

% ------------------ 页面与边距 ------------------
\RequirePackage[
  top=2.5cm,
  bottom=2.5cm,
  left=2.5cm,
  right=2.5cm,
  columnsep=1cm,
  headheight=62pt
]{geometry}

% ------------------ 中文支持 ------------------
\RequirePackage[UTF8, fontset=none]{ctex}
\IfFontExistsTF{Songti SC}{%
  \setCJKmainfont{Songti SC}[BoldFont=Songti SC Bold]
  \setCJKsansfont{Heiti SC}[BoldFont=Heiti SC Medium]
  \setCJKmonofont{Menlo}
}{%
  \IfFontExistsTF{SimSun}{%
    \setCJKmainfont{SimSun}[BoldFont=SimHei]
    \setCJKsansfont{Microsoft YaHei}[BoldFont=Microsoft YaHei Bold]
    \setCJKmonofont{SimSun}
  }{%
    \setCJKmainfont{FandolSong}[BoldFont=FandolHei]
    \setCJKsansfont{FandolHei}
    \setCJKmonofont{FandolFang}
  }%
}

% ------------------ 英文字体 ------------------
\RequirePackage{fontspec}
\IfFontExistsTF{Palatino}{%
  \setmainfont{Palatino}
}{%
  \IfFontExistsTF{Palatino Linotype}{%
    \setmainfont{Palatino Linotype}
  }{%
    \setmainfont{TeX Gyre Pagella}
  }%
}
\IfFontExistsTF{Helvetica Neue}{%
  \setsansfont{Helvetica Neue}
}{%
  \IfFontExistsTF{Arial}{%
    \setsansfont{Arial}
  }{%
    \setsansfont{TeX Gyre Heros}
  }%
}
\IfFontExistsTF{Menlo}{%
  \setmonofont{Menlo}[Scale=0.85]
}{%
  \IfFontExistsTF{Consolas}{%
    \setmonofont{Consolas}[Scale=0.85]
  }{%
    \setmonofont{TeX Gyre Cursor}[Scale=0.85]
  }%
}

% ------------------ 颜色定义 ------------------
\RequirePackage{xcolor}
% 主色调
\definecolor{primaryblue}{RGB}{41, 98, 255}
\definecolor{primarypurple}{RGB}{103, 58, 183}
\definecolor{primaryteal}{RGB}{0, 150, 136}
% 强调色
\definecolor{accentorange}{RGB}{255, 112, 67}
\definecolor{accentpink}{RGB}{236, 64, 122}
\definecolor{accentyellow}{RGB}{255, 193, 7}
% 背景色
\definecolor{bglight}{RGB}{250, 250, 252}
\definecolor{bgblue}{RGB}{232, 245, 253}
\definecolor{bggreen}{RGB}{232, 245, 233}
\definecolor{bgpurple}{RGB}{243, 229, 245}
\definecolor{bgorange}{RGB}{255, 243, 224}
\definecolor{bgpink}{RGB}{252, 228, 236}
% 文字颜色
\definecolor{textdark}{RGB}{33, 33, 33}
\definecolor{textgray}{RGB}{97, 97, 97}
\definecolor{codered}{RGB}{198, 40, 40}

% ------------------ 超链接样式 ------------------
\RequirePackage{hyperref}
\hypersetup{
  colorlinks=true,
  linkcolor=primaryblue,
  urlcolor=primaryteal,
  citecolor=primarypurple,
}

% ------------------ 盒子与框架 ------------------
\RequirePackage[most]{tcolorbox}

% 标题盒子
\newtcolorbox{titlebox}{
  enhanced,
  colback=bgblue,
  colframe=primaryblue,
  boxrule=2pt,
  arc=8pt,
  left=15pt, right=15pt, top=15pt, bottom=15pt,
  fonttitle=\bfseries\Large,
  shadow={2pt}{-2pt}{0pt}{black!30}
}

% 信息盒子
\newtcolorbox{infobox}[1][]{
  enhanced, colback=bgblue, colframe=primaryblue,
  fonttitle=\bfseries, title=#1,
  arc=4pt, boxrule=1pt, left=8pt, right=8pt
}

% 概念盒子
\newtcolorbox{conceptbox}[1][]{
  enhanced, colback=bgpurple, colframe=primarypurple,
  fonttitle=\bfseries, title=#1,
  arc=4pt, boxrule=1pt, left=8pt, right=8pt
}

% 创新点盒子
\newtcolorbox{innovationbox}[1][]{
  enhanced, colback=bggreen, colframe=primaryteal,
  fonttitle=\bfseries, title=#1,
  arc=4pt, boxrule=1pt, left=8pt, right=8pt
}

% 警告/注意盒子
\newtcolorbox{warningbox}[1][]{
  enhanced, colback=bgorange, colframe=accentorange,
  fonttitle=\bfseries, title=#1,
  arc=4pt, boxrule=1pt, left=8pt, right=8pt
}

% 代码盒子
\newtcolorbox{codebox}[1][]{
  enhanced, colback=bglight, colframe=textgray,
  fonttitle=\bfseries\ttfamily, title=#1,
  arc=3pt, boxrule=0.5pt, left=8pt, right=8pt, top=4pt, bottom=4pt
}

% 公式盒子
\newtcolorbox{equationbox}{
  enhanced, colback=bgpink, colframe=accentpink,
  arc=4pt, boxrule=1pt, left=10pt, right=10pt, top=8pt, bottom=8pt
}

% ------------------ 列表样式 ------------------
\RequirePackage{enumitem}
\setlist[itemize]{
  leftmargin=1.5em, itemsep=4pt, parsep=2pt,
  label=\textcolor{primaryblue}{\textbullet}
}
\setlist[enumerate]{
  leftmargin=1.5em, itemsep=4pt, parsep=2pt,
  label=\textcolor{primarypurple}{\arabic*.}
}

% ------------------ 标题样式 ------------------
\RequirePackage{titlesec}
\titleformat{\section}
  {\Large\bfseries\color{primaryblue}}
  {\thesection}{1em}{}
  [{\titlerule[1pt]}]
\titleformat{\subsection}
  {\large\bfseries\color{primarypurple}}
  {\thesubsection}{1em}{}
\titleformat{\subsubsection}
  {\normalsize\bfseries\color{primaryteal}}
  {\thesubsubsection}{1em}{}

\titlespacing{\section}{0pt}{15pt}{10pt}
\titlespacing{\subsection}{0pt}{12pt}{8pt}
\titlespacing{\subsubsection}{0pt}{10pt}{6pt}

% ------------------ 代码高亮 ------------------
\RequirePackage{listings}
\lstset{
  basicstyle=\ttfamily\small,
  keywordstyle=\color{primaryblue}\bfseries,
  commentstyle=\color{textgray}\itshape,
  stringstyle=\color{primaryteal},
  numberstyle=\tiny\color{textgray},
  numbers=left, numbersep=8pt,
  breaklines=true, breakatwhitespace=true,
  frame=none, backgroundcolor=\color{bglight},
  showstringspaces=false, tabsize=2, xleftmargin=15pt
}

% ------------------ 数学 ------------------
\RequirePackage{amsmath,amssymb,amsthm}
\RequirePackage{bm}

% ------------------ 表格 ------------------
\RequirePackage{booktabs}
\RequirePackage{array}
\RequirePackage{tabularx}
\RequirePackage{multirow}
\RequirePackage{colortbl}
\newcommand{\tableheadercolor}{\rowcolor{primaryblue!15}}
\newcommand{\tablerowcolor}{\rowcolor{bglight}}

% ------------------ 图片 ------------------
\RequirePackage{graphicx}
\RequirePackage{float}
\RequirePackage{subcaption}
\graphicspath{{../figure/}{../../figure/}}

% ------------------ 页眉 Logo ------------------
\RequirePackage{fancyhdr}
\RequirePackage{eso-pic}

\fancypagestyle{logostyle}{%
  \fancyhf{}
  \fancyhead[L]{\includegraphics[height=2cm]{logo.png}}
  \fancyfoot[C]{\thepage}
  \renewcommand{\headrulewidth}{0pt}
}
\pagestyle{logostyle}

% 标题页左上角 logo
\newcommand{\AddTitlePageLogo}{%
  \AddToShipoutPictureBG*{%
    \AtPageUpperLeft{%
      \raisebox{-3.5cm}{\hspace{1.5cm}\includegraphics[height=3cm]{logo.png}}%
    }%
  }%
}

% ------------------ 防止溢出 ------------------
\tolerance=1000
\emergencystretch=3em
\hyphenpenalty=5000
\exhyphenpenalty=5000
\raggedbottom
\setlist[itemize,enumerate]{leftmargin=*,rightmargin=0pt}

% ------------------ 自定义命令 ------------------
\newcommand{\hlblue}[1]{\textcolor{primaryblue}{\textbf{#1}}}
\newcommand{\hlpurple}[1]{\textcolor{primarypurple}{\textbf{#1}}}
\newcommand{\hlteal}[1]{\textcolor{primaryteal}{\textbf{#1}}}
\newcommand{\hlorange}[1]{\textcolor{accentorange}{\textbf{#1}}}
\newcommand{\hlbox}[2][yellow]{\colorbox{#1}{#2}}
\newcommand{\term}[1]{\textcolor{primarypurple}{\textbf{#1}}}

\endinput
