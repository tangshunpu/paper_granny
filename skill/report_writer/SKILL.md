---
name: report-writer
description: 如何使用 LaTeX 模板写解读报告。Agent 准备写报告时使用此技能，学习盒子环境和格式规范。
---

# 报告写作技能

## 报告结构

生成的报告应包含以下 section（可根据论文内容调整）：

```latex
\section{背景知识}          % 理解论文所需的前置知识
\section{核心问题与创新思路}  % 论文要解决什么？怎么创新？
\section{方法详解}          % 逐步解释方法，拆解公式
\section{实验结果}          % 解读实验图表
\section{总结}              % 核心贡献 + 局限性
\section{参考资料}          % 原论文引用
```

## 模板使用规则

### .cls 模板（推荐，大幅减少生成量）

先用 `read_template` 查看模板提供的盒子和命令，然后只需写：

```latex
\documentclass{ModernColorful}

\hypersetup{pdftitle={论文标题 深度解读}}

\begin{document}
% 标题页 + 目录 + 正文
\end{document}
```

**不需要复制任何 preamble 内容！** `compile_pdf` 会自动将 .cls 和 logo.png 复制到报告目录。

### .tex 模板（兼容旧模板）

1. 用 `read_template` 获取模板 preamble
2. 修改 preamble 中的标题、作者、日期、pdftitle
3. 拼接: preamble + `\begin{document}` + 标题页 + 目录 + 正文 + `\end{document}`

### 标题页模板

```latex
\begin{titlepage}
  \AddTitlePageLogo
  \thispagestyle{empty}
  \centering
  \vspace*{2cm}
  \begin{titlebox}
    \centering
    {\LARGE\bfseries\color{primaryblue} 论文标题}\\[10pt]
    {\Large\bfseries 论文深度解读}
  \end{titlebox}
  \vspace{2cm}
  {\large\color{textgray}
  \textbf{日期}：YYYY年MM月DD日
  }
  \vfill
  \begin{infobox}[论文信息]
    \centering
    \textbf{原文}：\href{https://arxiv.org/abs/XXXX.XXXXX}{arXiv:XXXX.XXXXX}
  \end{infobox}
\end{titlepage}

\tableofcontents
\newpage
```

## 盒子使用指南

| 盒子 | 颜色 | 用途 | 示例 |
|------|------|------|------|
| `infobox[标题]` | 蓝色 | 一般信息、实验配置 | 实验设置、论文信息 |
| `conceptbox[标题]` | 紫色 | 概念解释、背景知识 | 什么是推测解码 |
| `innovationbox[标题]` | 绿色 | 创新点、核心贡献 | 本文的核心创新 |
| `warningbox[标题]` | 橙色 | 注意事项、局限性 | 当前瓶颈、方法局限 |
| `equationbox` | 粉色 | 重要公式（无标题） | 核心目标函数 |
| `codebox[标题]` | 灰色 | 代码/伪代码 | 算法伪代码 |
| `titlebox` | 蓝色 | 标题/总结块 | 标题页、核心贡献 |

## 高亮命令

- `\hlblue{text}` — 蓝色加粗
- `\hlpurple{text}` — 紫色加粗
- `\hlteal{text}` — 青色加粗
- `\hlorange{text}` — 橙色加粗
- `\term{text}` — 紫色术语标记

## 图片引用

图片路径使用相对于 report.tex 的路径：

```latex
% 如果图片在 source/figures/ 目录
\includegraphics[width=\textwidth]{source/figures/fig1.pdf}
```

先用 `run_shell` 把图片复制到报告目录，或用相对路径引用。

## 常见错误与修复

| 错误 | 修复 |
|------|------|
| 文字溢出 margin | 在长公式/URL 前加 `\allowbreak` 或用 `\url{}` |
| 特殊字符报错 | 转义: `&` → `\&`, `%` → `\%`, `#` → `\#`, `_` → `\_` |
| 图片找不到 | 检查路径是否正确，用 `list_dir` 确认图片位置 |
| 编译超时 | 检查是否有无限循环的宏定义 |

## 编译

**使用 `compile_pdf` 工具（不要用 `run_shell` 手动调 xelatex）：**

```
compile_pdf("papers/{arxiv_id}/report.tex")
```

`compile_pdf` 会自动：
- 复制 .cls 模板文件到报告目录
- 复制 logo.png 到报告目录
- 编译并提取错误摘要
