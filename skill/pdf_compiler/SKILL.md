---
name: pdf-compiler
description: 将生成的 LaTeX 文件编译为 PDF，处理编译错误，清理中间文件。
---

# PDF 编译子技能

## 职责

调用 `compile_pdf` 工具将 `.tex` 文件编译为最终 PDF 报告。

## 编译方法

**务必使用 `compile_pdf` 工具，不要用 `run_shell` 手动调 xelatex。**

```
compile_pdf("papers/{arxiv_id}/report.tex")
```

`compile_pdf` 自动完成：
1. 使用 `xelatex -interaction=nonstopmode -halt-on-error` 编译（遇错即停，不会卡住）
2. 默认编译 2 遍（生成目录和交叉引用）
3. 从 `.log` 自动提取关键错误（行号 + 错误类型）
4. 编译成功后自动清理中间文件（`.aux`, `.log`, `.toc`, `.out` 等）

## 错误处理流程

当 `compile_pdf` 返回错误时：

1. **阅读错误摘要**：工具已从 log 中提取了关键错误和行号
2. **修改 .tex 文件**：根据错误修复对应行
3. **重新调用 `compile_pdf`**：不需要手动读 log

### 常见错误与修复

| 错误 | 修复 |
|------|------|
| 未定义命令 `\xxx` | 检查命令拼写，确认 preamble 中是否定义 |
| 缺少文件 | 用 `list_dir` 确认文件位置，修正路径 |
| 特殊字符报错 | 转义: `&` → `\&`, `%` → `\%`, `#` → `\#`, `_` → `\_` |
| 文字溢出 margin | 长 URL 用 `\url{}`，长公式加 `\allowbreak` |
| 字体缺失 | 提示用户安装 Noto CJK 系列字体 |

## 环境要求

- `xelatex` 编译器（TeX Live 或 MacTeX）
