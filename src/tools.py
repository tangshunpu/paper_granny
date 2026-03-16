"""
Agent 工具集

定义 Scholar Granny Agent 在 ReAct 循环中可使用的所有工具。
Agent 自行决定何时调用哪个工具来完成论文解读任务。
"""

import os
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

    返回每个模板的名称、文件大小和描述（从文件首行注释提取）。
    """
    template_dir = _project_root() / "latex_template"
    if not template_dir.exists():
        return "[ERROR] 模板目录不存在: latex_template/"

    templates = []
    for tex_file in sorted(template_dir.glob("*.tex")):
        size = tex_file.stat().st_size
        # 从首行注释提取描述
        try:
            first_line = tex_file.read_text(encoding="utf-8").split("\n")[0]
            desc = first_line.lstrip("% ").strip() if first_line.startswith("%") else ""
        except Exception:
            desc = ""
        templates.append(f"  📄 {tex_file.stem}  ({size / 1024:.1f} KB) — {desc}")

    if not templates:
        return "没有找到可用的 LaTeX 模板。请在 latex_template/ 目录下放置 .tex 模板文件。"

    return "📋 可用模板:\n" + "\n".join(templates)


@tool
def read_template(template_name: str) -> str:
    """读取指定模板的 preamble 部分（从 documentclass 到 begin{document}）。

    返回模板中定义的颜色、盒子环境、自定义命令等，
    供 Agent 在生成报告时正确使用这些样式。

    Args:
        template_name: 模板名称（不含 .tex 扩展名），如 "Modern Colorful"
    """
    template_dir = _project_root() / "latex_template"

    # 精确或模糊匹配
    found = None
    for tex_file in template_dir.glob("*.tex"):
        if tex_file.stem.lower() == template_name.lower():
            found = tex_file
            break
        if template_name.lower() in tex_file.stem.lower():
            found = tex_file

    if not found:
        available = [f.stem for f in template_dir.glob("*.tex")]
        return f"[ERROR] 未找到模板 '{template_name}'。可用: {available}"

    try:
        content = found.read_text(encoding="utf-8")
    except Exception as e:
        return f"[ERROR] 读取模板失败: {e}"

    # 提取 preamble
    import re
    match = re.search(r"(\\documentclass.*?)\\begin\{document\}", content, re.DOTALL)
    if match:
        preamble = match.group(1).strip()
        return f"📄 模板: {found.stem}\n\n=== PREAMBLE ===\n{preamble}"
    else:
        return f"📄 模板: {found.stem}\n\n(无法提取 preamble，返回完整内容前 300 行)\n" + \
               "\n".join(content.split("\n")[:300])


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
]
