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
1. 从 `latex_template/*/` 子目录复制所有 `.cls` 模板到报告目录（如 `ModernColorful.cls`）
2. 从 `figure/logo.png` 复制 logo 到报告目录（页眉和标题页需要）
3. 使用 `xelatex -interaction=nonstopmode -halt-on-error` 编译（遇错即停，不会卡住）
4. 默认编译 2 遍（生成目录和交叉引用）
5. 从 `.log` 自动提取**结构化错误报告**（见下方格式说明）
6. 编译成功后自动清理中间文件

## 错误报告格式

编译失败时，`compile_pdf` 返回以下结构化信息：

```
═══ 编译错误（共 N 条）═══

── 错误 #1 ──
  类型: Missing $ inserted
  位置: 第 367 行
  源码:
       365 | \begin{equationbox}
       366 | 条件概率可表示为：
    >> 367 | p(a_s | c, m_s) > p(a_s | c)
       368 | \end{equationbox}
       369 | 
  log 上下文: p(a_
  💡 修复提示: 数学符号（如 下标 _ 、上标 ^ ）必须在 $ $ 或数学环境中使用。

═══ 字体缺失字符（共 3 种）═══
  • → (U+2192)
  • ← (U+2190)
  💡 修复: Unicode 符号改用 LaTeX 命令，如 → 改为 $\rightarrow$

═══ 排版溢出警告（共 2 条）═══
  • 行 142: Overfull \hbox (15.2pt too wide)
  💡 修复: 长 URL 用 \url{}，长公式加 \allowbreak
```

**关键特性：**
- 每条错误自带 `.tex` 源码上下文（出错行用 `>>>` 标记），直接看到要改的代码
- 自动匹配修复提示，告诉你怎么修
- Missing character 警告去重汇总，不再被重复信息淹没

## 错误修复循环（必须严格遵循）

当 `compile_pdf` 返回错误时，执行以下循环：

```
┌─ compile_pdf ─────────────────────────────────┐
│  失败 → 读结构化错误 → edit_file(目标文件) → 重新 compile_pdf │
│  最多重试 3 次                                  │
│  成功 或 3 次仍失败 → 停止                       │
└──────────────────────────────────────────────┘
```

**关键规则：**
1. **编辑正确的文件**：每条错误都有 `文件:` 字段，编辑那个文件（可能是 `.cls`，不一定是 `report.tex`）
2. **用行号精确修复**：优先使用 `edit_file` 的行号模式 `{start_line, end_line, new_content}`
3. **最多重试 3 次**：如果 3 次编译仍失败，停止并报告剩余错误
4. **不要用 `write_file` 重写整个文件**！只用 `edit_file` 做局部修复

1. **阅读结构化错误报告**：每条错误都有行号、源码上下文和修复提示
2. **用 `edit_file` 按行号精确修复**（不要用 `write_file` 重写整个文件！）：

```python
# 按行号修复（错误报告中给出了行号和 >>> 标记的源码）
edit_file("papers/{arxiv_id}/report.tex", [
    {"start_line": 367, "end_line": 367, "new_content": "$p(a_s | c, m_s) > p(a_s | c)$"},
])

# 或按字符串匹配修复
edit_file("papers/{arxiv_id}/report.tex", [
    {"old_string": "p(a_s | c, m_s)", "new_string": "$p(a_s | c, m_s)$"},
])

# 可以一次修复多处错误
edit_file("papers/{arxiv_id}/report.tex", [
    {"start_line": 367, "end_line": 367, "new_content": "$p(a_s | c, m_s) > p(a_s | c)$"},
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
| Missing character in font | Unicode 符号（如 `→` `←` `⇒`）Palatino 不支持，改用 LaTeX 命令：`$\rightarrow$` `$\leftarrow$` `$\Rightarrow$` |
| Missing $ inserted | 数学符号必须在 `$ $` 或 `equation` 环境中 |
| Package kvsetkeys Error | 检查 `\hypersetup` 中的键值格式（逗号和等号） |

## 环境要求

- `xelatex` 编译器（TeX Live 或 MacTeX）
