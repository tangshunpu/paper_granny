"""
Agent 工具集

定义 Scholar Granny Agent 在 ReAct 循环中可使用的所有工具。
Agent 自行决定何时调用哪个工具来完成论文解读任务。
"""

import os
import re
import shutil
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


# ─── 论文下载工具（带缓存）──────────────────────────────────

def _extract_arxiv_id(url_or_id: str) -> str:
    """从 URL 或 ID 字符串中提取 arXiv ID。"""
    url_or_id = url_or_id.strip()
    # 匹配 arXiv ID 模式: YYMM.NNNNN 或旧格式 category/NNNNNNN
    patterns = [
        r"arxiv\.org/(?:abs|pdf|e-print)/(\d{4}\.\d{4,5}(?:v\d+)?)",
        r"arxiv\.org/(?:abs|pdf|e-print)/([\w.-]+/\d{7}(?:v\d+)?)",
        r"arXiv:(\d{4}\.\d{4,5}(?:v\d+)?)",
        r"^(\d{4}\.\d{4,5}(?:v\d+)?)$",
    ]
    for pat in patterns:
        m = re.search(pat, url_or_id)
        if m:
            return m.group(1)
    return url_or_id  # 原样返回，让后续步骤处理错误


@tool
def download_paper(arxiv_url: str) -> str:
    """下载 arXiv 论文 LaTeX 源码。自动提取 ID、下载、解压，并缓存已下载的论文。

    如果论文已下载过（papers/{id}/source/ 下有 .tex 文件），直接返回缓存结果，跳过下载。

    Args:
        arxiv_url: arXiv 论文 URL 或 ID，如 "https://arxiv.org/abs/2603.03251" 或 "2603.03251"
    """
    arxiv_id = _extract_arxiv_id(arxiv_url)
    root = _project_root()
    paper_dir = root / "papers" / arxiv_id
    source_dir = paper_dir / "source"
    tarball = paper_dir / "source.tar.gz"

    # ─── 缓存检查 ───
    if source_dir.exists():
        tex_files = list(source_dir.rglob("*.tex"))
        if tex_files:
            file_list = "\n".join(f"  📄 {f.relative_to(source_dir)}" for f in sorted(tex_files))
            return (
                f"✅ 论文已缓存，跳过下载\n"
                f"目录: papers/{arxiv_id}/source/\n"
                f"找到 {len(tex_files)} 个 .tex 文件:\n{file_list}"
            )

    # ─── 创建目录 ───
    source_dir.mkdir(parents=True, exist_ok=True)

    # ─── 下载 ───
    download_url = f"https://arxiv.org/e-print/{arxiv_id}"
    # 优先 curl（macOS 自带），其次 wget
    for cmd in [
        f'curl -L "{download_url}" -o "{tarball}"',
        f'wget "{download_url}" -O "{tarball}"',
    ]:
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=str(root),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0 and tarball.exists() and tarball.stat().st_size > 0:
                break
        except Exception:
            continue
    else:
        return f"[ERROR] 下载失败: {download_url}\n请检查网络连接或论文 ID 是否正确。"

    # ─── 解压 ───
    # 尝试 tar.gz
    try:
        result = subprocess.run(
            f'tar -xzf "{tarball}" -C "{source_dir}"',
            shell=True, capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            # 可能是单个 gzip 文件
            subprocess.run(
                f'gunzip -c "{tarball}" > "{source_dir}/main.tex"',
                shell=True, capture_output=True, text=True, timeout=60,
            )
    except Exception as e:
        return f"[ERROR] 解压失败: {e}"

    # ─── 验证 ───
    tex_files = list(source_dir.rglob("*.tex"))
    if not tex_files:
        return (
            f"[WARNING] 下载并解压完成，但未找到 .tex 文件。\n"
            f"目录: papers/{arxiv_id}/source/\n"
            f"此论文可能没有 LaTeX 源码，请用 list_dir 检查目录内容。"
        )

    file_list = "\n".join(f"  📄 {f.relative_to(source_dir)}" for f in sorted(tex_files))
    size = tarball.stat().st_size
    size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"

    return (
        f"✅ 下载并解压成功\n"
        f"目录: papers/{arxiv_id}/source/\n"
        f"源码包: {size_str}\n"
        f"找到 {len(tex_files)} 个 .tex 文件:\n{file_list}"
    )


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


# ─── 文件编辑工具 ────────────────────────────────────────────

@tool
def edit_file(path: str, edits: list[dict]) -> str:
    """对文件进行局部编辑，不需要重写整个文件。修复编译错误时优先使用此工具。

    支持两种编辑模式，可在一次调用中混合使用：

    1. 行号范围替换（适合编译错误修复，log 已给出行号）：
       {"start_line": 42, "end_line": 42, "new_content": "修复后的内容"}
       - start_line 和 end_line 均为 1-indexed，包含两端
       - 删除行：new_content 设为 ""
       - 插入行：start_line 设为插入位置，end_line 设为 start_line - 1

    2. 字符串匹配替换（适合修改特定代码片段）：
       {"old_string": "要替换的文本", "new_string": "替换后的文本"}
       - old_string 必须在文件中唯一匹配
       - 可包含多行（用 \\n 分隔）

    Args:
        path: 文件路径（相对于项目根目录，或绝对路径）
        edits: 编辑操作列表，每个元素是上述两种格式之一
    """
    file_path = _resolve_path(path)
    if not file_path.exists():
        return f"[ERROR] 文件不存在: {file_path}"

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"[ERROR] 读取失败: {e}"

    lines = content.split("\n")
    results = []

    # 按行号倒序处理行范围编辑（从后往前改，避免行号偏移）
    line_edits = []
    string_edits = []

    for i, edit in enumerate(edits):
        if "start_line" in edit:
            line_edits.append((i, edit))
        elif "old_string" in edit:
            string_edits.append((i, edit))
        else:
            results.append(f"编辑 #{i+1}: [跳过] 格式不正确，需要 start_line/end_line 或 old_string/new_string")

    # 先处理字符串替换（在行编辑之前，因为行号可能改变）
    for i, edit in string_edits:
        old = edit["old_string"]
        new = edit.get("new_string", "")
        count = content.count(old)

        if count == 0:
            # 不做静默模糊替换 — 返回明确失败和候选行供 agent 确认
            old_stripped = old.strip()
            candidate_lines = []
            for line_idx, line in enumerate(lines):
                if old_stripped in line.strip():
                    candidate_lines.append(f"  行 {line_idx+1}: {line.rstrip()[:80]}")
            if candidate_lines:
                candidates_str = "\n".join(candidate_lines[:3])
                results.append(
                    f"编辑 #{i+1}: [失败] 精确匹配未找到。"
                    f"以下行包含相似内容（请用精确文本或行号重试）:\n{candidates_str}"
                )
            else:
                results.append(f"编辑 #{i+1}: [失败] 未找到匹配: {old[:60]}...")
        elif count > 1:
            results.append(f"编辑 #{i+1}: [失败] 匹配到 {count} 处，需要唯一匹配: {old[:60]}...")
        else:
            content = content.replace(old, new, 1)
            lines = content.split("\n")
            results.append(f"编辑 #{i+1}: ✅ 字符串替换成功")

    # 再处理行范围编辑（倒序，避免行号偏移）
    line_edits.sort(key=lambda x: x[1].get("start_line", 0), reverse=True)
    for i, edit in line_edits:
        start = edit["start_line"]
        end = edit.get("end_line", start)
        new_content = edit.get("new_content", "")

        if start < 1 or end < 0 or start > len(lines) + 1:
            results.append(f"编辑 #{i+1}: [失败] 行号越界 (start={start}, end={end}, 文件共 {len(lines)} 行)")
            continue

        # 转为 0-indexed
        start_idx = start - 1
        end_idx = end  # lines[start_idx:end_idx] 包含 start 到 end

        new_lines = new_content.split("\n") if new_content else []
        old_preview = " | ".join(lines[start_idx:min(end_idx, start_idx + 3)])
        lines[start_idx:end_idx] = new_lines

        if new_content:
            results.append(f"编辑 #{i+1}: ✅ 替换行 {start}-{end} ({end - start + 1} 行 → {len(new_lines)} 行)")
        elif end >= start:
            results.append(f"编辑 #{i+1}: ✅ 删除行 {start}-{end}")
        else:
            results.append(f"编辑 #{i+1}: ✅ 在行 {start} 前插入 {len(new_lines)} 行")

    # 写回文件
    content = "\n".join(lines)
    try:
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        return f"[ERROR] 写回失败: {e}"

    total_lines = len(lines)
    return f"📝 已编辑 {file_path} ({total_lines} 行)\n" + "\n".join(results)


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

    每个模板是一个子目录，包含同名 .cls 文件。
    例如 latex_template/ModernColorful/ModernColorful.cls。
    .cls 模板推荐使用，agent 只需写 \\documentclass{Name} + 正文即可。
    """
    template_dir = _project_root() / "latex_template"
    if not template_dir.exists():
        return "[ERROR] 模板目录不存在: latex_template/"

    templates = []
    for sub in sorted(template_dir.iterdir()):
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        cls_file = sub / f"{sub.name}.cls"
        if not cls_file.exists():
            # 也尝试查找目录内任意 .cls 文件
            cls_files = list(sub.glob("*.cls"))
            if not cls_files:
                continue
            cls_file = cls_files[0]
        size = cls_file.stat().st_size
        try:
            first_line = cls_file.read_text(encoding="utf-8").split("\n")[0]
            desc = first_line.lstrip("% ").strip() if first_line.startswith("%") else ""
        except Exception:
            desc = ""
        templates.append(f"  📄 [CLS] {cls_file.stem}  ({size / 1024:.1f} KB) — {desc}")

    if not templates:
        return "没有找到可用的 LaTeX 模板。请在 latex_template/<模板名>/ 目录下放置同名 .cls 模板文件。"

    return "📋 可用模板:\n" + "\n".join(templates)


@tool
def read_template(template_name: str) -> str:
    """读取指定模板的信息，返回可用的盒子环境、命令和使用示例。

    对于 .cls 模板，只需 \\documentclass{TemplateName} 即可使用，
    无需复制 preamble，大幅减少报告生成量。

    Args:
        template_name: 模板名称（不含扩展名），如 "ModernColorful"
    """
    template_dir = _project_root() / "latex_template"
    found = _find_template_cls(template_dir, template_name)

    if not found:
        available = [d.name for d in template_dir.iterdir()
                     if d.is_dir() and not d.name.startswith(".") and list(d.glob("*.cls"))]
        return f"[ERROR] 未找到模板 '{template_name}'。可用: {available}"

    try:
        content = found.read_text(encoding="utf-8")
    except Exception as e:
        return f"[ERROR] 读取模板失败: {e}"

    # 提取可用环境和命令的摘要
    boxes = re.findall(r"\\newtcolorbox\{(\w+)\}", content)
    commands = re.findall(r"\\newcommand\{\\(\w+)\}", content)
    colors = re.findall(r"\\definecolor\{(\w+)\}", content)

    cls_name = found.stem
    result = f"📄 模板: {cls_name} (.cls)\n\n"
    result += f"## 使用方式\n\n"
    result += f"只需一行即可引入所有样式，无需复制 preamble：\n"
    result += f"```latex\n\\documentclass{{{cls_name}}}\n```\n\n"
    result += f"compile_pdf 会自动将 .cls 和 logo.png 复制到报告目录。\n\n"
    result += f"## 可用盒子环境\n\n"
    for box in boxes:
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


def _find_template_cls(template_dir: Path, template_name: str) -> Optional[Path]:
    """在 template_dir 的子目录中查找与 template_name 匹配的 .cls 文件。"""
    name_normalized = template_name.lower().replace(" ", "")
    for sub in template_dir.iterdir():
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        if sub.name.lower().replace(" ", "") == name_normalized:
            cls_file = sub / f"{sub.name}.cls"
            if cls_file.exists():
                return cls_file
            cls_files = list(sub.glob("*.cls"))
            if cls_files:
                return cls_files[0]
    return None


# ─── PDF 编译工具 ────────────────────────────────────────────

# 编译中间文件后缀
_LATEX_AUX_EXTENSIONS = {".aux", ".log", ".out", ".toc", ".synctex.gz", ".fls", ".fdb_latexmk", ".nav", ".snm", ".vrb"}

# 常见错误的自动修复提示
_FIX_HINTS = {
    "Undefined control sequence": "检查命令拼写，确认模板是否提供该命令。只用 SKILL.md 中列出的命令。",
    "Missing $ inserted": "数学符号（如 下标 _ 、上标 ^ 、希腊字母）必须在 $ $ 或数学环境中使用。",
    "Missing \\endcsname inserted": "检查是否在 \\hypersetup 等键值参数中用了不匹配的花括号或特殊字符。",
    "File": "用 list_dir 确认文件位置，修正路径或复制文件到报告目录。",
    "Missing number": "检查长度/计数器参数是否正确，如 \\hspace{} 中是否遗漏了数值。",
    "Illegal unit of measure": "长度值需要单位，如 1cm、10pt、0.5\\textwidth。",
    "Environment": "检查 \\begin{xxx} 和 \\end{xxx} 是否配对，环境名是否拼写正确。",
    "Too many }'s": "多余的 }，检查花括号配对。",
    "Extra alignment tab": "表格中 & 的数量超过列数，检查 tabular/tabularx 的列定义。",
    "Overfull \\hbox": "内容溢出页面边距。长 URL 用 \\url{}，长公式加 \\allowbreak。",
    "Package kvsetkeys Error": "键值参数格式错误，检查 \\hypersetup 等命令中的逗号和等号。",
}


def _get_fix_hint(error_msg: str) -> str:
    """根据错误信息返回修复提示。"""
    for keyword, hint in _FIX_HINTS.items():
        if keyword.lower() in error_msg.lower():
            return hint
    return ""


def _get_source_context(tex_path: Path, line_num: int, context: int = 2) -> str:
    """读取 .tex 文件中指定行号附近的源码，用于错误定位。

    Args:
        tex_path: .tex 文件路径
        line_num: 错误行号 (1-indexed)
        context: 上下文行数（前后各取几行）

    Returns:
        带行号的源码片段，出错行用 >>> 标记
    """
    try:
        lines = tex_path.read_text(encoding="utf-8", errors="replace").split("\n")
    except Exception:
        return ""

    if line_num < 1 or line_num > len(lines):
        return ""

    start = max(0, line_num - 1 - context)
    end = min(len(lines), line_num + context)

    result_lines = []
    for i in range(start, end):
        ln = i + 1  # 1-indexed
        marker = ">>>" if ln == line_num else "   "
        result_lines.append(f"    {marker} {ln:4d} | {lines[i]}")

    return "\n".join(result_lines)


def _extract_log_errors(log_path: Path, tex_path: Path, max_errors: int = 10) -> str:
    """从 .log 文件中提取结构化错误信息。

    使用状态机逐行扫描，将 ! 错误与后续 l.XXX 行号配对。
    同时收集 Missing character 警告和 Overfull/Underfull 警告。

    Returns:
        格式化的错误报告字符串（包含行号、错误描述、源码上下文、修复提示）
    """
    if not log_path.exists():
        return "[log 文件不存在]"

    try:
        log_content = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "[无法读取 log 文件]"

    log_lines = log_content.split("\n")

    # ── 状态机解析：配对 ! Error 和 l.XXX ──
    errors: list[dict] = []
    missing_chars: set[str] = set()
    overflow_warnings: list[str] = []
    current_error: dict | None = None

    # file-line-error 格式: ./report.tex:123: error message
    # 支持 ./ 前缀、无前缀 (bare)、绝对路径
    re_file_line = re.compile(r"^(?:\./)?((?:[A-Za-z]:[\\/]|/)?.+?\.(?:tex|cls|sty)):(\d+): (.+)$")
    # 标准错误: ! Error message
    re_bang_error = re.compile(r"^! (.+)$")
    # 行号: l.123 context
    re_line_num = re.compile(r"^l\.(\d+) (.*)$")
    # Package/Class 错误
    re_package_error = re.compile(r"^! (Package|Class) (\w+) Error: (.+)$")
    # Missing character 警告
    re_missing_char = re.compile(r"Missing character: There is no (.+?) \((.+?)\) in font")
    # Overfull/Underfull 警告
    re_overflow = re.compile(r"^((?:Over|Under)full \\[hv]box .+?) at lines? (\d+)(?:--(\d+))?")

    def _finalize_error():
        nonlocal current_error
        if current_error and len(errors) < max_errors:
            errors.append(current_error)
        current_error = None

    for line in log_lines:
        line_stripped = line.rstrip()

        # 1) file-line-error 格式
        m = re_file_line.match(line_stripped)
        if m:
            _finalize_error()
            current_error = {
                "file": m.group(1),
                "line": int(m.group(2)),
                "message": m.group(3),
                "context_from_log": "",
            }
            continue

        # 2) Package/Class 错误（优先于通用 ! 匹配）
        m = re_package_error.match(line_stripped)
        if m:
            _finalize_error()
            pkg_type = m.group(1)
            pkg_name = m.group(2)
            pkg_msg = m.group(3)
            current_error = {
                "file": "",
                "line": 0,
                "message": f"{pkg_type} {pkg_name} Error: {pkg_msg}",
                "context_from_log": "",
            }
            continue

        # 3) 标准 ! 错误
        m = re_bang_error.match(line_stripped)
        if m:
            # 如果已有 file-line-error 正在处理，它已经有消息了，
            # 这个 ! 行通常是同一个错误的重复，跳过
            if current_error and current_error.get("line", 0) > 0:
                # 已通过 file-line-error 捕获，补充消息
                if not current_error["message"] or current_error["message"] == line_stripped:
                    pass
                continue
            _finalize_error()
            current_error = {
                "file": "",
                "line": 0,
                "message": m.group(1),
                "context_from_log": "",
            }
            continue

        # 4) l.XXX 行号 — 关联到当前错误
        m = re_line_num.match(line_stripped)
        if m:
            line_num = int(m.group(1))
            log_context = m.group(2)
            if current_error:
                if current_error["line"] == 0:
                    current_error["line"] = line_num
                current_error["context_from_log"] = log_context
                _finalize_error()
            else:
                # 孤立的 l.XXX（不太常见）
                if len(errors) < max_errors:
                    errors.append({
                        "file": "",
                        "line": line_num,
                        "message": f"(错误上下文) {log_context}",
                        "context_from_log": log_context,
                    })
            continue

        # 5) Missing character 警告
        m = re_missing_char.search(line_stripped)
        if m:
            char_desc = m.group(1).strip()
            char_code = m.group(2).strip()
            missing_chars.add(f"{char_desc} ({char_code})")
            continue

        # 6) Overfull/Underfull 警告
        m = re_overflow.match(line_stripped)
        if m:
            if len(overflow_warnings) < 3:  # 只保留前 3 条
                overflow_warnings.append(f"行 {m.group(2)}: {m.group(1)}")
            continue

    # 处理最后一个未关闭的错误
    _finalize_error()

    # ── 格式化输出 ──
    if not errors and not missing_chars and not overflow_warnings:
        return "[未能从 log 提取具体错误，请用 read_file 查看 .log 文件手动排查]"

    parts = []

    # 主要错误
    if errors:
        parts.append(f"═══ 编译错误（共 {len(errors)} 条）═══\n")
        for idx, err in enumerate(errors, 1):
            line_num = err["line"]
            msg = err["message"]
            err_file = err.get("file", "")
            hint = _get_fix_hint(msg)

            parts.append(f"── 错误 #{idx} ──")
            parts.append(f"  类型: {msg}")

            # 确定源码文件：优先使用 error 中解析出的文件，回退到 tex_path
            if err_file:
                # 显示错误所在文件
                parts.append(f"  文件: {err_file}")
                # 解析源文件路径用于获取上下文
                err_file_path = Path(err_file)
                if not err_file_path.is_absolute():
                    err_file_path = tex_path.parent / err_file_path
                source_file = err_file_path if err_file_path.exists() else tex_path
            else:
                source_file = tex_path

            if line_num > 0:
                parts.append(f"  位置: 第 {line_num} 行")
                # 附加源码上下文（从正确的文件读取）
                src_ctx = _get_source_context(source_file, line_num)
                if src_ctx:
                    parts.append(f"  源码:")
                    parts.append(src_ctx)
            if err["context_from_log"]:
                parts.append(f"  log 上下文: {err['context_from_log']}")
            if hint:
                parts.append(f"  💡 修复提示: {hint}")
            parts.append("")

    # Missing character 警告
    if missing_chars:
        chars_list = sorted(missing_chars)
        parts.append(f"═══ 字体缺失字符（共 {len(chars_list)} 种）═══")
        for ch in chars_list[:10]:  # 最多显示 10 种
            parts.append(f"  • {ch}")
        if len(chars_list) > 10:
            parts.append(f"  ... 还有 {len(chars_list) - 10} 种")
        parts.append("  💡 修复: Unicode 符号改用 LaTeX 命令，如 → 改为 $\\rightarrow$")
        parts.append("")

    # Overflow 警告
    if overflow_warnings:
        parts.append(f"═══ 排版溢出警告（共 {len(overflow_warnings)} 条）═══")
        for w in overflow_warnings:
            parts.append(f"  • {w}")
        parts.append("  💡 修复: 长 URL 用 \\url{}，长公式加 \\allowbreak")
        parts.append("")

    return "\n".join(parts)


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
    - 自动从 .log 提取结构化错误（行号 + 错误类型 + 源码上下文 + 修复提示）
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
    # 从所有模板子目录复制 .cls 文件
    for sub in template_dir.iterdir():
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        for cls_file in sub.glob("*.cls"):
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
            error_report = _extract_log_errors(log_path, file_path)
            return (
                f"[编译失败] 第 {i}/{runs} 遍\n"
                f"文件: {file_path}\n\n"
                f"{error_report}\n"
                f"请根据以上错误信息，使用 edit_file 修改对应的文件"
                f"（见每条错误的「文件」字段）后重新调用 compile_pdf。"
            )

    # 检查 PDF 输出
    if not pdf_path.exists():
        return f"[ERROR] 编译似乎成功但未生成 PDF: {pdf_path}"

    # 将 PDF 重命名为 arxiv ID（父目录名），例如 report.pdf → 2603.03251.pdf
    arxiv_id = report_dir.name
    final_pdf_path = report_dir / f"{arxiv_id}.pdf"
    if pdf_path != final_pdf_path:
        # 删除旧的同名文件（如果存在）
        if final_pdf_path.exists():
            final_pdf_path.unlink()
        pdf_path.rename(final_pdf_path)
        pdf_path = final_pdf_path

    pdf_size = pdf_path.stat().st_size
    size_str = f"{pdf_size / 1024:.1f} KB" if pdf_size < 1024 * 1024 else f"{pdf_size / 1024 / 1024:.1f} MB"

    # 成功时也检查警告（Missing character 等）
    warnings = ""
    if log_path.exists():
        warn_report = _extract_log_errors(log_path, file_path)
        # 只有在有实际警告内容时才附加（非"未能提取"开头）
        if warn_report and not warn_report.startswith("[未能从"):
            # 过滤只保留警告部分（非"编译错误"部分）
            warn_lines = []
            in_warning_section = False
            for line in warn_report.split("\n"):
                if "字体缺失字符" in line or "排版溢出警告" in line:
                    in_warning_section = True
                if "编译错误" in line:
                    in_warning_section = False
                if in_warning_section:
                    warn_lines.append(line)
            if warn_lines:
                warnings = "\n\n⚠️ 编译警告（不影响 PDF 生成，但建议修复）:\n" + "\n".join(warn_lines)

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
    if warnings:
        result += warnings
    return result


# ─── 图片信息工具 ─────────────────────────────────────────────

@tool
def get_image_info(path: str) -> str:
    """获取目录下所有图片的尺寸信息，用于在 LaTeX 中设置合适的 includegraphics 宽度。

    扫描指定目录下的所有图片文件（.png, .jpg, .jpeg, .pdf, .eps），
    返回每张图片的：宽度×高度（像素/点）、宽高比、文件大小、建议的 LaTeX 宽度参数。

    **在 report.tex 中使用 \includegraphics 之前务必先调用此工具！**

    Args:
        path: 图片所在目录路径（相对于项目根目录，或绝对路径）
    """
    dir_path = _resolve_path(path)
    if not dir_path.exists():
        return f"[ERROR] 目录不存在: {dir_path}"
    if not dir_path.is_dir():
        # 如果传入了单个文件，取其父目录
        dir_path = dir_path.parent

    image_exts = {".png", ".jpg", ".jpeg", ".pdf", ".eps"}
    images = sorted(
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in image_exts
    )

    if not images:
        return f"[INFO] 目录 {dir_path} 中没有找到图片文件（.png/.jpg/.pdf/.eps）"

    results = []
    results.append(f"📸 图片信息（{dir_path}，共 {len(images)} 张）\n")
    results.append(f"{'文件名':<30s} {'尺寸(px/pt)':<18s} {'宽高比':<8s} {'大小':<10s} {'建议 LaTeX 宽度'}")
    results.append("─" * 95)

    for img_path in images:
        name = img_path.name
        size = img_path.stat().st_size
        size_str = f"{size / 1024:.1f}KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f}MB"

        w, h = _get_dimensions(img_path)

        if w > 0 and h > 0:
            ratio = w / h
            ratio_str = f"{ratio:.2f}"
            dim_str = f"{w}×{h}"
            # 根据宽高比和绝对宽度推荐 LaTeX 宽度
            latex_width = _recommend_latex_width(w, h, img_path.suffix.lower())
        else:
            ratio_str = "?"
            dim_str = "未知"
            latex_width = "0.8\\textwidth"

        results.append(f"{name:<30s} {dim_str:<18s} {ratio_str:<8s} {size_str:<10s} {latex_width}")

    results.append("")
    results.append("💡 使用示例:")
    if images:
        sample = images[0]
        sample_w, sample_h = _get_dimensions(sample)
        lw = _recommend_latex_width(sample_w, sample_h, sample.suffix.lower()) if sample_w > 0 else "0.8\\textwidth"
        results.append(f"  \\includegraphics[width={lw}]{{{sample.name}}}")

    return "\n".join(results)


def _get_dimensions(img_path: Path) -> tuple[int, int]:
    """获取图片的宽高（像素或点）。支持 PNG/JPG (Pillow) 和 PDF (pdfinfo/sips)。"""
    suffix = img_path.suffix.lower()

    # PNG/JPG: 尝试 Pillow
    if suffix in (".png", ".jpg", ".jpeg"):
        try:
            from PIL import Image
            with Image.open(img_path) as im:
                return im.size  # (width, height)
        except Exception:
            pass
        # fallback: macOS sips
        try:
            result = subprocess.run(
                ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(img_path)],
                capture_output=True, text=True, timeout=5,
            )
            w = h = 0
            for line in result.stdout.split("\n"):
                if "pixelWidth" in line:
                    w = int(line.split(":")[-1].strip())
                if "pixelHeight" in line:
                    h = int(line.split(":")[-1].strip())
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass

    # PDF: 尝试 pdfinfo
    if suffix == ".pdf":
        try:
            result = subprocess.run(
                ["pdfinfo", str(img_path)],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.split("\n"):
                if "Page size" in line:
                    # 格式: "Page size:      612 x 792 pts (letter)"
                    m = re.search(r"([\d.]+)\s*x\s*([\d.]+)", line)
                    if m:
                        return int(float(m.group(1))), int(float(m.group(2)))
        except Exception:
            pass
        # fallback: macOS mdls
        try:
            result = subprocess.run(
                ["mdls", "-name", "kMDItemPageWidth", "-name", "kMDItemPageHeight", str(img_path)],
                capture_output=True, text=True, timeout=5,
            )
            w = h = 0
            for line in result.stdout.split("\n"):
                if "kMDItemPageWidth" in line and "(null)" not in line:
                    w = int(float(line.split("=")[-1].strip()))
                if "kMDItemPageHeight" in line and "(null)" not in line:
                    h = int(float(line.split("=")[-1].strip()))
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass

    return 0, 0


def _recommend_latex_width(w: int, h: int, suffix: str) -> str:
    """根据图片尺寸推荐 LaTeX \includegraphics 的 width 参数。"""
    if w <= 0 or h <= 0:
        return "0.8\\textwidth"

    ratio = w / h

    # PDF 图片通常是矢量图，尺寸单位是 pt (1pt ≈ 0.35mm)
    # \textwidth ≈ 455pt (A4, 1in margin each side)
    if suffix == ".pdf":
        if w > 600:  # 很宽的图
            return "\\textwidth"
        elif w > 400:
            return "0.9\\textwidth"
        elif ratio > 1.8:  # 宽型图
            return "0.85\\textwidth"
        elif ratio < 0.6:  # 高型/窄图
            return "0.45\\textwidth"
        else:
            return "0.7\\textwidth"

    # 光栅图 (PNG/JPG)，通常 DPI ≈ 72-300
    # 预估: 150dpi → 1px ≈ 0.5pt, 所以 455pt ≈ 910px
    if w > 1200:  # 很宽
        return "\\textwidth"
    elif w > 800:
        return "0.9\\textwidth"
    elif ratio > 1.8:  # 宽型
        return "0.85\\textwidth"
    elif ratio < 0.6:  # 高型/窄图
        return "0.4\\textwidth"
    elif w < 400:  # 小图
        return "0.5\\textwidth"
    else:
        return "0.7\\textwidth"


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
    download_paper,
    read_file,
    write_file,
    edit_file,
    list_dir,
    list_templates,
    read_template,
    read_skill,
    compile_pdf,
    get_image_info,
]
