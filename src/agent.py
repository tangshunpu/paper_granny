"""
Scholar Granny ReAct Agent

基于 LangGraph 的 ReAct Agent，自主探索论文源码并生成解读报告。
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .tools import ALL_TOOLS
from .skills import build_system_prompt

console = Console()


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
                        content_preview = args.get("content", "")[:100] + "..."
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
