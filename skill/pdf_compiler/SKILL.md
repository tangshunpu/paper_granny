---
name: pdf-compiler
description: 将生成的 LaTeX 文件编译为 PDF，处理编译错误，清理中间文件。
---

# PDF 编译子技能

## 职责

调用 LaTeX 编译器将 `.tex` 文件编译为最终 PDF 报告。

## 编译流程

1. 运行 `xelatex` 第一遍（生成 `.aux` 等辅助文件）
2. 运行 `xelatex` 第二遍（生成目录和交叉引用）
3. 检查编译结果
4. 清理中间文件（`.aux`, `.log`, `.toc`, `.out` 等）

## 错误处理

- 编译错误：解析 `.log` 文件定位错误行，尝试自动修复常见问题
- 字体缺失：提示安装所需中文字体（Noto CJK 系列）
- 编译超时：设置 60 秒超时保护

## 环境要求

- `xelatex` 编译器（TeX Live 或 MacTeX）
- 中文字体：Noto Serif/Sans/Mono CJK SC
