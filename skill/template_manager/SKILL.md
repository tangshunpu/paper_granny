---
name: template-manager
description: 管理 LaTeX 模板目录，提供模板发现、加载和信息展示功能。
---

# 模板管理子技能

## 职责

管理 `latex_template/` 目录下的 LaTeX 模板，为用户提供模板选择。

## 模板目录结构

每个模板是一个子目录，包含同名 `.cls` 文件：

```
latex_template/
└── ModernColorful/
    ├── ModernColorful.cls    # 模板类文件（必须）
    └── Modern Colorful.tex   # 示例文档（可选）
```

## 功能

### 模板发现
- 扫描 `latex_template/` 下的子目录
- 每个子目录视为一个模板，查找内部同名 `.cls` 文件
- Agent 只需写 `\documentclass{ModernColorful}` + 正文即可

### 模板信息解析
- 提取模板中定义的颜色方案
- 提取自定义盒子类型（`infobox`, `conceptbox` 等）
- 提取自定义命令（`\hlblue`, `\term` 等）

### 模板使用
- `compile_pdf` 自动将 `.cls` 和 `logo.png` 复制到报告目录
- 不需要复制 preamble，不需要手动操作

## 添加新模板

在 `latex_template/` 下创建子目录，放入同名 `.cls` 文件即可：
```
latex_template/MyTemplate/MyTemplate.cls
```
