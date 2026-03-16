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
1. 复制 .cls 模板和 logo.png 到报告目录
2. 使用 `xelatex -interaction=nonstopmode -halt-on-error` 编译（遇错即停，不会卡住）
3. 默认编译 2 遍（生成目录和交叉引用）
4. 从 `.log` 自动提取关键错误（行号 + 错误类型）
5. 编译成功后自动清理中间文件

## 错误修复流程

当 `compile_pdf` 返回错误时：

1. **阅读错误摘要**：工具已提取了行号和错误类型
2. **用 `edit_file` 修复**（不要用 `write_file` 重写整个文件！）：

```python
# 按行号修复（错误摘要中给出了行号）
edit_file("papers/{arxiv_id}/report.tex", [
    {"start_line": 42, "end_line": 42, "new_content": "修复后的那一行"},
])

# 或按字符串匹配修复
edit_file("papers/{arxiv_id}/report.tex", [
    {"old_string": "\\badcommand{text}", "new_string": "\\goodcommand{text}"},
])

# 可以一次修复多处错误
edit_file("papers/{arxiv_id}/report.tex", [
    {"start_line": 42, "end_line": 42, "new_content": "修复行42"},
    {"old_string": "未转义的&", "new_string": "转义的\\&"},
])
```

3. **重新调用 `compile_pdf`**

### 常见错误与修复

| 错误 | 修复 |
|------|------|
| 未定义命令 `\xxx` | 检查命令拼写，确认模板是否提供该命令 |
| 缺少文件 | 用 `list_dir` 确认文件位置，修正路径 |
| 特殊字符报错 | 转义: `&` → `\&`, `%` → `\%`, `#` → `\#`, `_` → `\_` |
| 文字溢出 margin | 长 URL 用 `\url{}`，长公式加 `\allowbreak` |
| 字体缺失 | 提示用户安装对应字体 |

## 环境要求

- `xelatex` 编译器（TeX Live 或 MacTeX）
