---
name: report-writer
description: 如何使用 LaTeX 模板写解读报告。Agent 准备写报告时使用此技能，学习盒子环境和格式规范。
---

# 报告写作技能

## ⚠️ 核心原则：严格使用模板命令

**报告中只能使用 cls 模板已定义的环境和命令。不要自创命令、不要 `\newcommand`、不要添加额外的 `\usepackage`。**

模板 `ModernColorful.cls` 已加载所有需要的包，包括：
`geometry`, `ctex`, `fontspec`, `xcolor`, `hyperref`, `tcolorbox`, `enumitem`, `titlesec`, `listings`, `amsmath/amssymb/amsthm`, `bm`, `booktabs`, `array`, `tabularx`, `multirow`, `colortbl`, `graphicx`, `float`, `subcaption`, `fancyhdr`, `eso-pic`


## 报告结构

```latex
\section{背景知识}          % 理解论文所需的前置知识
\section{核心问题与创新思路}  % 论文要解决什么？怎么创新？
\section{方法详解}          % 逐步解释方法，拆解公式
\section{实验结果}          % 解读实验图表
\section{总结}              % 核心贡献 + 局限性
\section{参考资料}          % 原论文引用
```


**不需要复制任何 preamble！** `compile_pdf` 会自动将 .cls 和 logo.png 复制到报告目录。

## 模板使用规则

**不需要复制 preamble！** 用 `read_template` 了解可用的盒子和命令即可。


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

## 可用盒子环境（只能用这些）

| 环境 | 用法 | 颜色 | 用途 |
|------|------|------|------|
| `titlebox` | `\begin{titlebox}...\end{titlebox}` | 蓝色+阴影 | 标题页、总结块 |
| `infobox` | `\begin{infobox}[标题]...\end{infobox}` | 蓝色 | 一般信息、实验配置 |
| `conceptbox` | `\begin{conceptbox}[标题]...\end{conceptbox}` | 紫色 | 概念解释、背景知识 |
| `innovationbox` | `\begin{innovationbox}[标题]...\end{innovationbox}` | 绿色 | 创新点、核心贡献 |
| `warningbox` | `\begin{warningbox}[标题]...\end{warningbox}` | 橙色 | 注意事项、局限性 |
| `equationbox` | `\begin{equationbox}...\end{equationbox}` | 粉色 | 重要公式（无标题） |
| `codebox` | `\begin{codebox}[标题]...\end{codebox}` | 灰色 | 代码/伪代码 |

## 可用高亮命令（只能用这些）

| 命令 | 效果 |
|------|------|
| `\hlblue{text}` | 蓝色加粗 |
| `\hlpurple{text}` | 紫色加粗 |
| `\hlteal{text}` | 青色加粗 |
| `\hlorange{text}` | 橙色加粗 |
| `\term{text}` | 紫色术语标记 |
| `\hlbox[颜色]{text}` | 背景高亮 |

## 可用颜色名（只能用这些）

- 主色：`primaryblue`, `primarypurple`, `primaryteal`
- 强调：`accentorange`, `accentpink`, `accentyellow`
- 背景：`bglight`, `bgblue`, `bggreen`, `bgpurple`, `bgorange`, `bgpink`
- 文字：`textdark`, `textgray`, `codered`

## 可用表格命令

- `\tableheadercolor` — 表头行背景色
- `\tablerowcolor` — 交替行背景色

## 其他可用命令

- `\AddTitlePageLogo` — 标题页左上角添加 logo
- 页面自动使用 `logostyle` 页眉（左上 logo + 页码）

## 图片处理（重要！编写报告前先做）

**所有图片必须在 report.tex 同目录下，cls 不设置 `\graphicspath`。**

1. 用 `list_dir` 查看 `source/` 中的图片（通常在 `source/figures/` 或 `source/figs/`）
2. 用 `run_shell` 复制需要的图片到报告目录：

```python
run_shell("cp papers/{arxiv_id}/source/figures/*.pdf papers/{arxiv_id}/")
run_shell("cp papers/{arxiv_id}/source/figures/*.png papers/{arxiv_id}/")
```

3. **用 `get_image_info` 读取所有图片的尺寸**（复制后必做！）：

```python
get_image_info("papers/{arxiv_id}/")
```

返回每张图片的宽×高、宽高比、建议的 LaTeX 宽度参数，例如：
```
📸 图片信息（papers/1512.03385/，共 6 张）

文件名                         尺寸(px/pt)       宽高比   大小       建议 LaTeX 宽度
─────────────────────────────────────────────────────────────────────────────────
arch.pdf                       684×710           0.96     26.5KB     0.7\textwidth
block.pdf                      324×218           1.49     11.2KB     0.7\textwidth
teaser.pdf                     520×380           1.37     18.3KB     0.85\textwidth
```

4. **按建议宽度写 `\includegraphics`**：

```latex
% 使用 get_image_info 返回的建议宽度，不要盲目用 \textwidth
\includegraphics[width=0.7\textwidth]{arch.pdf}
\includegraphics[width=0.85\textwidth]{teaser.pdf}
```

## 常见错误与修复

| 错误 | 修复 |
|------|------|
| 未定义命令 `\xxx` | **只用上面列出的命令！** 不要自创命令 |
| 文字溢出 margin | 长 URL 用 `\url{}`，长公式加 `\allowbreak` |
| 特殊字符报错 | 转义: `&` → `\&`, `%` → `\%`, `#` → `\#`, `_` → `\_` |
| 图片找不到 | 确认已复制到报告目录，用 `list_dir` 验证 |
| Missing character in font | Unicode 符号（如 `→` `←` `⇒`）Palatino 不支持，改用 LaTeX 命令：`$\rightarrow$` `$\leftarrow$` `$\Rightarrow$` |

## 编译

**使用 `compile_pdf` 工具（不要用 `run_shell` 手动调 xelatex）：**

```
compile_pdf("papers/{arxiv_id}/report.tex")
```

`compile_pdf` 会自动：
- 从 `latex_template/*/` 子目录复制 `.cls` 模板文件到报告目录
- 从 `figure/logo.png` 复制 logo 到报告目录
- 编译并提取错误摘要
