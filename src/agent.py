"""
Scholar Granny ReAct Agent

基于 LangGraph 的 ReAct Agent，自主探索论文源码并生成解读报告。
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .tools import ALL_TOOLS
from .skills import build_system_prompt

console = Console()


# ─── 上下文管理 ──────────────────────────────────────────────
# Agent 工作分为多个阶段，前一阶段的详细 tool 输出在进入下一阶段后
# 可以被压缩为摘要，避免 messages 无限膨胀撑爆 context window。

# 阶段定义：通过 tool 调用模式识别当前阶段
STAGES = [
    # (阶段名, 进入条件: 出现过的 tool_call 模式)
    ("download",    lambda tc: tc["name"] == "read_skill" and "arxiv_downloader" in tc["args"].get("skill_name", "")),
    ("read_source", lambda tc: tc["name"] == "read_file" and "source/" in tc["args"].get("path", "")),
    ("interpret",   lambda tc: tc["name"] == "read_skill" and "paper_interpreter" in tc["args"].get("skill_name", "")),
    ("template",    lambda tc: tc["name"] in ("read_template", "read_skill") and
                     ("template" in tc["args"].get("template_name", "") or "report_writer" in tc["args"].get("skill_name", "") or "template" in tc["args"].get("skill_name", ""))),
    ("write",       lambda tc: tc["name"] == "write_file" and "report" in tc["args"].get("path", "")),
    ("compile",     lambda tc: tc["name"] == "run_shell" and "xelatex" in tc["args"].get("command", "")),
]

# 每个阶段结束后，哪些 tool 的输出可以被压缩
STAGE_COMPRESSIBLE_TOOLS = {
    "download":    {"run_shell"},         # wget/tar 的输出
    "read_source": {"read_file"},         # .tex 源码全文
    "interpret":   {"read_skill"},        # 技能指南（已内化）
    "template":    {"read_template", "read_skill"},
}

# tool 输出超过此长度才压缩，避免压缩短消息
COMPRESS_THRESHOLD = 500


def _detect_current_stage(messages) -> str:
    """根据历史 tool_calls 检测当前所处阶段。"""
    current = "init"
    for msg in messages:
        if not hasattr(msg, "tool_calls") or not msg.tool_calls:
            continue
        for tc in msg.tool_calls:
            for stage_name, matcher in STAGES:
                try:
                    if matcher(tc):
                        current = stage_name
                except Exception:
                    continue
    return current


def _get_passed_stages(messages) -> list[str]:
    """返回已经经历过的阶段列表（不含当前阶段）。"""
    seen = []
    current = "init"
    for msg in messages:
        if not hasattr(msg, "tool_calls") or not msg.tool_calls:
            continue
        for tc in msg.tool_calls:
            for stage_name, matcher in STAGES:
                try:
                    if matcher(tc) and stage_name != current:
                        if current != "init" and current not in seen:
                            seen.append(current)
                        current = stage_name
                except Exception:
                    continue
    return seen


def _compress_messages(state) -> dict:
    """
    pre_model_hook: 在每轮 LLM 调用前裁剪上下文。

    策略：已完成阶段的大段 tool 输出替换为摘要行，
    保留 SystemMessage、HumanMessage、最近阶段的完整内容。
    """
    messages = state["messages"]

    passed_stages = _get_passed_stages(messages)
    if not passed_stages:
        return {"llm_input_messages": messages}

    # 收集已完成阶段可压缩的 tool 名称
    compressible_tools = set()
    for stage in passed_stages:
        compressible_tools |= STAGE_COMPRESSIBLE_TOOLS.get(stage, set())

    if not compressible_tools:
        return {"llm_input_messages": messages}

    current_stage = _detect_current_stage(messages)

    # 找到当前阶段开始的位置（从后往前找）
    current_stage_start = len(messages)
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                for stage_name, matcher in STAGES:
                    try:
                        if matcher(tc) and stage_name == current_stage:
                            current_stage_start = i
                    except Exception:
                        continue

    trimmed = []
    # 构建 tool_call id -> AI message 的映射，用于保持 tool_call/ToolMessage 配对一致
    for i, msg in enumerate(messages):
        # 保留 System/Human 消息
        if isinstance(msg, (SystemMessage, HumanMessage)):
            trimmed.append(msg)
            continue

        # 当前阶段及之后的消息完整保留
        if i >= current_stage_start:
            trimmed.append(msg)
            continue

        # ToolMessage: 检查是否属于可压缩的 tool
        if isinstance(msg, ToolMessage):
            tool_name = msg.name or ""
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if tool_name in compressible_tools and len(content) > COMPRESS_THRESHOLD:
                trimmed.append(ToolMessage(
                    content=f"[已完成 - {tool_name} 输出已压缩，共 {len(content)} 字符]",
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                ))
                continue

        # 其他消息保留
        trimmed.append(msg)

    return {"llm_input_messages": trimmed}


def create_scholar_agent(
    llm: BaseChatModel,
    template_name: Optional[str] = None,
    language: str = "中文",
    extra_instructions: str = "",
):
    """
    创建 Scholar Granny ReAct Agent。

    Args:
        llm: LangChain ChatModel 实例
        template_name: 指定使用的 LaTeX 模板
        language: 报告输出语言
        extra_instructions: 额外指令

    Returns:
        LangGraph Agent (可 invoke)
    """
    system_prompt = build_system_prompt(
        template_name=template_name,
        language=language,
        extra_instructions=extra_instructions,
    )

    agent = create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=system_prompt,
        pre_model_hook=_compress_messages,
    )

    return agent


def run_agent(
    agent,
    arxiv_url: str,
    template_name: Optional[str] = None,
    verbose: bool = True,
) -> str:
    """
    运行 Agent 解读论文。
    
    Args:
        agent: LangGraph Agent
        arxiv_url: arXiv 论文 URL 或 ID
        template_name: 使用的模板名称
        verbose: 是否打印详细的 Agent 推理过程
        
    Returns:
        Agent 最终回复
    """
    # 构建用户任务消息
    task_parts = [f"请解读这篇 arXiv 论文: {arxiv_url}"]

    if template_name:
        task_parts.append(f"使用 LaTeX 模板: {template_name}")

    task_parts.append(
        "\n请按以下步骤自主工作:\n"
        "1. 先读取 arxiv_downloader 技能指南，下载并解压论文 LaTeX 源码\n"
        "2. 探索源码目录结构，找到主 tex 文件\n"
        "3. 深度阅读论文源码（包括所有 \\input 引用的文件）\n"
        "4. 读取 paper_interpreter 技能指南，学习解读方法\n"
        "5. 读取模板 preamble，了解可用的盒子和命令\n"
        "6. 读取 report_writer 技能指南，学习报告写作规范\n"
        "7. 生成完整的 LaTeX 解读报告 (使用模板的 preamble + 你的解读内容)\n"
        "8. 编译 PDF（xelatex 运行两次）\n"
        "9. 报告最终结果\n"
    )

    user_message = "\n".join(task_parts)

    if verbose:
        console.print(Panel(
            user_message,
            title="📋 Agent 任务",
            border_style="blue",
        ))

    # 运行 Agent
    final_response = ""

    if verbose:
        console.print("\n[bold]🧠 Agent 开始推理...[/]\n")

    result = agent.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": 150},
    )

    # 提取消息并打印
    for msg in result["messages"]:
        if verbose:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc["name"]
                    args = tc["args"]
                    # 简化显示
                    if tool_name == "write_file":
                        console.print(f"  [yellow]🔧 {tool_name}[/]({args.get('path', '')})")
                    elif tool_name == "run_shell":
                        console.print(f"  [yellow]🔧 {tool_name}[/](`{args.get('command', '')}`)")
                    elif tool_name == "read_file":
                        console.print(f"  [yellow]🔧 {tool_name}[/]({args.get('path', '')})")
                    elif tool_name == "list_dir":
                        console.print(f"  [yellow]🔧 {tool_name}[/]({args.get('path', '.')})")
                    else:
                        console.print(f"  [yellow]🔧 {tool_name}[/]({args})")

            elif hasattr(msg, "content") and msg.content and msg.type == "ai":
                if not getattr(msg, "tool_calls", None):
                    final_response = msg.content

    if verbose and final_response:
        console.print("\n")
        console.print(Panel(
            Markdown(final_response),
            title="✅ Agent 完成",
            border_style="green",
        ))

    return final_response
