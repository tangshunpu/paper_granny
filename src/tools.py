"""
Agent 工具集

定义 Scholar Granny Agent 在 ReAct 循环中可使用的所有工具。
Agent 自行决定何时调用哪个工具来完成论文解读任务。
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


# ─── 项目路径 ────────────────────────────────────────────────

def _project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent


def _resolve_path(path: str) -> Path:
    """解析路径：相对路径基于项目根，绝对路径保持不变"""
    p = Path(path)
    if p.is_absolute():
        return p
    return _project_root() / p


# ─── Shell 工具 ──────────────────────────────────────────────

@tool
def run_shell(command: str, cwd: Optional[str] = None) -> str:
    """执行 shell 命令并返回输出。

    用于：下载论文 (wget/curl)、解压 (tar)、编译 PDF (xelatex)、
    查看文件类型、安装依赖等系统操作。

    Args:
        command: 要执行的 shell 命令字符串
        cwd: 工作目录，默认为项目根目录。可以是绝对路径或相对于项目根的路径。
    """
    work_dir = str(_resolve_path(cwd)) if cwd else str(_project_root())
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        if result.returncode != 0:
            output += f"\n[EXIT CODE: {result.returncode}]"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "[ERROR] 命令执行超时 (120s)"
    except Exception as e:
        return f"[ERROR] 命令执行失败: {e}"


# ─── 文件读取工具 ────────────────────────────────────────────

@tool
def read_file(path: str, start_line: int = 1, max_lines: int = 200) -> str:
    """读取文件内容。

    用于：阅读论文 .tex 源码、.bib 参考文献、
    .sty 样式文件、README 等文本文件。

    Args:
        path: 文件路径（相对于项目根目录，或绝对路径）
        start_line: 从第几行开始读（1-indexed），默认从头开始
        max_lines: 最多读取多少行，默认 200 行。如果文件更长，会提示继续读。
    """
    file_path = _resolve_path(path)
    if not file_path.exists():
        return f"[ERROR] 文件不存在: {file_path}"
    if not file_path.is_file():
        return f"[ERROR] 不是文件: {file_path}"

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[ERROR] 读取失败: {e}"

    lines = content.split("\n")
    total_lines = len(lines)

    # 调整为 0-indexed
    start_idx = max(0, start_line - 1)
    end_idx = min(start_idx + max_lines, total_lines)

    selected = lines[start_idx:end_idx]
    result = "\n".join(selected)

    if end_idx < total_lines:
        result += f"\n\n[... 文件共 {total_lines} 行，已显示 {start_line}-{end_idx} 行。" \
                  f"调用 read_file(\"{path}\", start_line={end_idx + 1}) 继续阅读]"

    return result


# ─── 文件写入工具 ────────────────────────────────────────────

@tool
def write_file(path: str, content: str) -> str:
    """写入文件内容。如果文件已存在则覆盖，目录不存在则自动创建。

    用于：生成 LaTeX 解读报告、写辅助脚本等。

    Args:
        path: 文件路径（相对于项目根目录，或绝对路径）
        content: 要写入的完整文件内容
    """
    file_path = _resolve_path(path)
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        size = file_path.stat().st_size
        return f"✅ 文件已写入: {file_path} ({size} bytes)"
    except Exception as e:
        return f"[ERROR] 写入失败: {e}"


# ─── 目录列出工具 ────────────────────────────────────────────

@tool
def list_dir(path: str = ".") -> str:
    """列出目录下的文件和子目录，显示文件类型和大小。

    用于：探索解压后的论文源码目录结构，
    了解有哪些 tex 文件、图片、子目录等。

    Args:
        path: 目录路径（相对于项目根目录，或绝对路径），默认为项目根。
    """
    dir_path = _resolve_path(path)
    if not dir_path.exists():
        return f"[ERROR] 目录不存在: {dir_path}"
    if not dir_path.is_dir():
        return f"[ERROR] 不是目录: {dir_path}"

    entries = []
    try:
        for item in sorted(dir_path.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                count = sum(1 for _ in item.rglob("*") if _.is_file())
                entries.append(f"  📁 {item.name}/  ({count} files)")
            else:
                size = item.stat().st_size
                if size > 1024 * 1024:
                    size_str = f"{size / 1024 / 1024:.1f} MB"
                elif size > 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size} B"
                entries.append(f"  📄 {item.name}  ({size_str})")
    except Exception as e:
        return f"[ERROR] 列出目录失败: {e}"

    if not entries:
        return f"(空目录: {dir_path})"

    header = f"📂 {dir_path}\n"
    return header + "\n".join(entries)


# ─── 模板相关工具 ────────────────────────────────────────────

@tool
def list_templates() -> str:
    """列出 latex_template/ 目录下所有可用的 LaTeX 模板。

    返回每个模板的名称、类型（.cls 或 .tex）、文件大小和描述。
    .cls 模板推荐使用，agent 只需写 \\documentclass{Name} + 正文即可。
    """
    template_dir = _project_root() / "latex_template"
    if not template_dir.exists():
        return "[ERROR] 模板目录不存在: latex_template/"

    templates = []
    for pattern in ("*.cls", "*.tex"):
        for f in sorted(template_dir.glob(pattern)):
            size = f.stat().st_size
            try:
                first_line = f.read_text(encoding="utf-8").split("\n")[0]
                desc = first_line.lstrip("% ").strip() if first_line.startswith("%") else ""
            except Exception:
                desc = ""
            tag = "[CLS]" if f.suffix == ".cls" else "[TEX]"
            templates.append(f"  📄 {tag} {f.stem}  ({size / 1024:.1f} KB) — {desc}")

    if not templates:
        return "没有找到可用的 LaTeX 模板。请在 latex_template/ 目录下放置 .cls 或 .tex 模板文件。"

    return "📋 可用模板:\n" + "\n".join(templates)


@tool
def read_template(template_name: str) -> str:
    """读取指定模板的信息，返回可用的盒子环境、命令和使用示例。

    对于 .cls 模板，只需 \\documentclass{TemplateName} 即可使用，
    无需复制 preamble，大幅减少报告生成量。

    Args:
        template_name: 模板名称（不含扩展名），如 "Modern Colorful" 或 "ModernColorful"
    """
    template_dir = _project_root() / "latex_template"

    # 搜索 .cls 和 .tex 文件，优先 .cls
    found = None
    for ext in (".cls", ".tex"):
        for f in template_dir.glob(f"*{ext}"):
            if f.stem.lower() == template_name.lower().replace(" ", ""):
                found = f
                break
            if f.stem.lower() == template_name.lower():
                found = f
                break
            if template_name.lower().replace(" ", "") in f.stem.lower():
                found = f
        if found:
            break

    if not found:
        available = [f.stem for f in template_dir.glob("*.cls")] + \
                    [f.stem for f in template_dir.glob("*.tex")]
        return f"[ERROR] 未找到模板 '{template_name}'。可用: {available}"

    try:
        content = found.read_text(encoding="utf-8")
    except Exception as e:
        return f"[ERROR] 读取模板失败: {e}"

    # .cls 模板：提取可用环境和命令的摘要，而非完整 preamble
    if found.suffix == ".cls":
        # 提取 tcolorbox 环境名
        boxes = re.findall(r"\\newtcolorbox\{(\w+)\}", content)
        # 提取自定义命令
        commands = re.findall(r"\\newcommand\{\\(\w+)\}", content)
        # 提取颜色名
        colors = re.findall(r"\\definecolor\{(\w+)\}", content)

        cls_name = found.stem
        result = f"📄 模板: {cls_name} (.cls)\n\n"
        result += f"## 使用方式\n\n"
        result += f"只需一行即可引入所有样式，无需复制 preamble：\n"
        result += f"```latex\n\\documentclass{{{cls_name}}}\n```\n\n"
        result += f"编译时需要将 {cls_name}.cls 复制到报告目录，或设置 TEXINPUTS。\n\n"
        result += f"## 可用盒子环境\n\n"
        for box in boxes:
            # 查找盒子定义附近的注释作为描述
            pattern = rf"% (.+?)\n\\newtcolorbox\{{{box}\}}"
            desc_match = re.search(pattern, content)
            desc = desc_match.group(1) if desc_match else ""
            result += f"- `{box}` — {desc}\n"
        result += f"\n## 可用高亮命令\n\n"
        for cmd in commands:
            result += f"- `\\{cmd}{{text}}`\n"
        result += f"\n## 可用颜色\n\n"
        result += ", ".join(f"`{c}`" for c in colors)
        result += f"\n\n## 其他说明\n\n"
        result += f"- `\\AddTitlePageLogo` — 标题页左上角 logo\n"
        result += f"- 页面默认使用 `logostyle` 页眉（左上 logo + 页码）\n"
        result += f"- 需要 logo.png 在报告同目录下\n"
        return result

    # .tex 模板：返回 preamble（旧逻辑兼容）
    match = re.search(r"(\\documentclass.*?)\\begin\{document\}", content, re.DOTALL)
    if match:
        preamble = match.group(1).strip()
        return f"📄 模板: {found.stem}\n\n=== PREAMBLE ===\n{preamble}"
    else:
        return f"📄 模板: {found.stem}\n\n(无法提取 preamble，返回完整内容前 300 行)\n" + \
               "\n".join(content.split("\n")[:300])


# ─── PDF 编译工具 ────────────────────────────────────────────

# 从 .log 中提取关键错误的正则模式
_LATEX_ERROR_PATTERNS = [
    # 标准 LaTeX 错误: ! Error message
    (re.compile(r"^! (.+)$", re.MULTILINE), "error"),
    # 带行号的错误: l.123 some context
    (re.compile(r"^l\.(\d+) (.*)$", re.MULTILINE), "line"),
    # 未定义的控制序列
    (re.compile(r"Undefined control sequence.*\n.*\\(\w+)", re.MULTILINE), "undef"),
    # 缺少文件
    (re.compile(r"File `(.+?)' not found", re.MULTILINE), "missing_file"),
    # 字体缺失
    (re.compile(r"Font .+? at \d+ not found|cannot find (.+?) font", re.MULTILINE | re.IGNORECASE), "font"),
    # Package 错误
    (re.compile(r"Package (\w+) Error: (.+?)(?:\n|$)", re.MULTILINE), "package"),
]

# 编译中间文件后缀
_LATEX_AUX_EXTENSIONS = {".aux", ".log", ".out", ".toc", ".synctex.gz", ".fls", ".fdb_latexmk", ".nav", ".snm", ".vrb"}


def _extract_log_errors(log_path: Path, max_errors: int = 5) -> list[str]:
    """从 .log 文件中提取关键错误信息，避免返回整个 log。"""
    if not log_path.exists():
        return ["[log 文件不存在]"]

    try:
        log_content = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ["[无法读取 log 文件]"]

    errors = []
    for pattern, kind in _LATEX_ERROR_PATTERNS:
        for match in pattern.finditer(log_content):
            if kind == "error":
                errors.append(f"! {match.group(1)}")
            elif kind == "line":
                errors.append(f"  → 行 {match.group(1)}: {match.group(2)}")
            elif kind == "undef":
                errors.append(f"未定义命令: \\{match.group(1)}")
            elif kind == "missing_file":
                errors.append(f"缺少文件: {match.group(1)}")
            elif kind == "font":
                errors.append(f"字体问题: {match.group(0).strip()}")
            elif kind == "package":
                errors.append(f"Package {match.group(1)}: {match.group(2)}")
            if len(errors) >= max_errors:
                break
        if len(errors) >= max_errors:
            break

    return errors if errors else ["[未能从 log 提取具体错误，请检查 .log 文件]"]


def _run_xelatex(tex_path: Path, timeout: int = 60) -> tuple[bool, str]:
    """运行一次 xelatex 编译，返回 (成功?, 输出摘要)。"""
    cmd = [
        "xelatex",
        "-interaction=nonstopmode",  # 遇到错误不等待输入，直接跳过
        "-halt-on-error",            # 遇到严重错误立即停止，不浪费时间
        "-file-line-error",          # 输出 file:line:error 格式，方便定位
        tex_path.name,
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(tex_path.parent),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        success = result.returncode == 0
        return success, result.stdout[-500:] if result.stdout else ""
    except subprocess.TimeoutExpired:
        return False, f"[编译超时 ({timeout}s)]"
    except FileNotFoundError:
        return False, "[错误] 未找到 xelatex 命令，请安装 TeX Live 或 MacTeX"
    except Exception as e:
        return False, f"[错误] {e}"


@tool
def compile_pdf(tex_path: str, runs: int = 2, cleanup: bool = True) -> str:
    """编译 LaTeX 文件为 PDF。自动使用 xelatex 并提取错误信息。

    比直接用 run_shell 调 xelatex 更快更可靠：
    - 使用 nonstopmode + halt-on-error，遇错立即停止不会卡住
    - 自动从 .log 提取关键错误（行号 + 错误类型），无需手动读 log
    - 自动清理中间文件

    Args:
        tex_path: .tex 文件路径（相对于项目根目录，或绝对路径）
        runs: 编译次数，默认 2（第二遍生成目录和交叉引用）
        cleanup: 编译成功后是否清理中间文件（.aux/.log/.out/.toc 等）
    """
    file_path = _resolve_path(tex_path)
    if not file_path.exists():
        return f"[ERROR] 文件不存在: {file_path}"
    if not file_path.suffix == ".tex":
        return f"[ERROR] 不是 .tex 文件: {file_path}"

    log_path = file_path.with_suffix(".log")
    pdf_path = file_path.with_suffix(".pdf")
    report_dir = file_path.parent
    template_dir = _project_root() / "latex_template"

    # 自动复制模板依赖文件到报告目录
    import shutil
    # 复制所有 .cls 文件（模板类文件）
    for cls_file in template_dir.glob("*.cls"):
        dest = report_dir / cls_file.name
        if not dest.exists():
            shutil.copy2(cls_file, dest)
    # 复制 logo.png（模板页眉/标题页需要）
    logo_src = _project_root() / "figure" / "logo.png"
    logo_dest = report_dir / "logo.png"
    if logo_src.exists() and not logo_dest.exists():
        shutil.copy2(logo_src, logo_dest)

    # 多遍编译
    for i in range(1, runs + 1):
        success, output = _run_xelatex(file_path)

        if not success:
            errors = _extract_log_errors(log_path)
            error_report = "\n".join(errors)
            return (
                f"[编译失败] 第 {i}/{runs} 遍\n"
                f"文件: {file_path}\n\n"
                f"错误摘要（共 {len(errors)} 条）:\n{error_report}\n\n"
                f"请根据以上错误修改 .tex 文件后重新调用 compile_pdf。"
            )

    # 检查 PDF 输出
    if not pdf_path.exists():
        return f"[ERROR] 编译似乎成功但未生成 PDF: {pdf_path}"

    pdf_size = pdf_path.stat().st_size
    size_str = f"{pdf_size / 1024:.1f} KB" if pdf_size < 1024 * 1024 else f"{pdf_size / 1024 / 1024:.1f} MB"

    # 清理中间文件
    cleaned = []
    if cleanup:
        for ext in _LATEX_AUX_EXTENSIONS:
            aux_file = file_path.with_suffix(ext)
            if aux_file.exists():
                aux_file.unlink()
                cleaned.append(ext)

    result = f"✅ 编译成功！\nPDF: {pdf_path} ({size_str})"
    if cleaned:
        result += f"\n已清理: {', '.join(cleaned)}"
    return result


# ─── Skill 工具 ──────────────────────────────────────────────

@tool
def read_skill(skill_name: str) -> str:
    """读取指定子技能的 SKILL.md 指南。

    Agent 可以在需要时主动阅读技能指南来学习：
    - arxiv_downloader: 如何下载 arXiv 论文源码
    - latex_reader: 如何阅读和探索 LaTeX 源码
    - paper_interpreter: 如何深度解读论文（术语白话化、公式拆解等）
    - report_writer: 如何使用模板盒子写 LaTeX 报告
    - pdf_compiler: 如何编译 PDF
    - template_manager: 如何选择和使用模板

    Args:
        skill_name: 技能名称，如 "paper_interpreter"
    """
    skill_dir = _project_root() / "skill" / skill_name
    skill_file = skill_dir / "SKILL.md"

    if not skill_file.exists():
        # 列出可用技能
        skill_root = _project_root() / "skill"
        available = [d.name for d in skill_root.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
        return f"[ERROR] 未找到技能 '{skill_name}'。可用技能: {available}"

    try:
        content = skill_file.read_text(encoding="utf-8")
        return f"📖 技能指南: {skill_name}\n\n{content}"
    except Exception as e:
        return f"[ERROR] 读取技能失败: {e}"


# ─── 工具注册 ───────────────────────────────────────────────

ALL_TOOLS = [
    run_shell,
    read_file,
    write_file,
    list_dir,
    list_templates,
    read_template,
    read_skill,
    compile_pdf,
]
