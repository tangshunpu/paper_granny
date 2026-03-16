---
name: template-manager
description: 管理 LaTeX 模板目录，提供模板发现、加载和信息展示功能。
---

# 模板管理子技能

## 职责

管理 `latex_template/` 目录下的 LaTeX 模板，为用户提供模板选择。

## 功能

### 模板发现
- 扫描 `latex_template/` 目录下所有 `.tex` 文件
- 从文件名派生模板显示名称

### 模板信息解析
- 提取模板中定义的颜色方案
- 提取自定义盒子类型（`infobox`, `conceptbox` 等）
- 提取自定义命令（`\hlblue`, `\term` 等）

### 模板加载
- 分离 preamble（`\documentclass` 到 `\begin{document}` 之间）
- 提取 document body 的结构模板
- 提供填充接口供 report_generator 使用

## 模板约定

模板 `.tex` 文件的第一行注释可包含描述信息：
```latex
% 美观多彩的技术文档模板 - Modern Colorful Template
```
