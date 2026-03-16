---
name: latex-reader
description: 如何自适应地探索和阅读 LaTeX 论文源码。当 Agent 下载完论文后需要阅读源码时使用此技能。
---

# LaTeX 源码阅读技能

## 探索策略

1. **先 `list_dir` 看结构**：了解有哪些文件和子目录
2. **找主文件**：找包含 `\documentclass` 的 `.tex` 文件（通常是 `main.tex` 或 `paper.tex`）
3. **读主文件**：用 `read_file` 阅读主文件
4. **追踪引用**：找到 `\input{xxx}` 或 `\include{xxx}`，逐个阅读引用的文件
5. **读参考文献**：如果有 `.bib` 文件，也要阅读

## 阅读重点

### 必须阅读
- 主 tex 文件（整体结构）
- 方法部分（核心贡献）
- 实验部分（结果验证）
- 摘要和引言
- 所有 `\input` 引用的文件

### 注意事项
- 大文件用分段读取：`read_file("path", start_line=1, max_lines=200)`
- 留意 `\newcommand` 和 `\def` 定义的缩写
- 留意 `\begin{theorem}`, `\begin{proposition}` 等定理环境
- 记录图片路径（`\includegraphics{...}`）供报告引用

## 常见目录结构

```
source/
├── main.tex          # 主文件
├── introduction.tex  # 引言
├── method.tex        # 方法
├── experiments.tex   # 实验
├── conclusion.tex    # 结论
├── figures/          # 图片
│   ├── fig1.pdf
│   └── fig2.png
├── tables/           # 表格
├── refs.bib          # 参考文献
└── macros.tex        # 宏定义
```

## 信息提取清单

阅读时请提取：
- [ ] 论文标题和作者
- [ ] 研究问题和动机
- [ ] 核心方法和算法
- [ ] 所有关键公式（保留 LaTeX 原文）
- [ ] 定理/命题/引理的原始表述
- [ ] 实验设置和结果
- [ ] 图片文件路径
- [ ] 关键术语列表
