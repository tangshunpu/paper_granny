"""
Scholar Granny — arXiv 论文解读 Agent

CLI 入口。基于 LangGraph ReAct Agent 自主解读论文。
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from .config import load_config, AppConfig
from .llm_factory import create_llm
from .agent import create_scholar_agent, run_agent
from .tools import list_templates as list_templates_tool

console = Console()

BANNER = r"""
  ╔══════════════════════════════════════════════════╗
  ║  📖  Scholar Granny  v0.2.0                      ║
  ║  arXiv 论文智能解读 — LangGraph ReAct Agent        ║
  ╚══════════════════════════════════════════════════╝
"""


@click.group(invoke_without_command=True)
@click.option("--url", "-u", help="arXiv 论文 URL 或 ID")
@click.option("--provider", "-p", help="LLM provider (openai/claude/ollama/vllm)")
@click.option("--model", "-m", help="模型名称")
@click.option("--api-key", "-k", help="API Key")
@click.option("--base-url", help="自定义 API 地址 (vLLM/Ollama)")
@click.option("--template", "-t", help="LaTeX 模板名称")
@click.option("--output", "-o", help="输出目录")
@click.option("--config-file", "-c", help="配置文件路径", default=None)
@click.option("--quiet", "-q", is_flag=True, help="静默模式，不打印推理过程")
@click.pass_context
def cli(ctx, url, provider, model, api_key, base_url, template, output, config_file, quiet):
    """Scholar Granny — arXiv 论文智能解读 Agent"""
    ctx.ensure_object(dict)

    if ctx.invoked_subcommand is not None:
        return

    if not url:
        console.print(BANNER)
        console.print("使用 [bold]--help[/] 查看帮助，或使用 [bold]--url[/] 指定论文。\n")
        console.print("[bold]示例:[/]")
        console.print("  [cyan]python -m src.main --url https://arxiv.org/abs/2603.03251[/]")
        console.print("  [cyan]python -m src.main --url 2603.03251 -p claude -m claude-sonnet-4-20250514[/]")
        console.print("  [cyan]python -m src.main --url 2603.03251 -p ollama -m llama3[/]")
        console.print("  [cyan]python -m src.main list-templates[/]")
        console.print("  [cyan]python -m src.main config[/]")
        return

    # 加载配置
    config = load_config(config_file)

    # CLI 参数覆盖配置文件
    if provider:
        config.llm.provider = provider
    if model:
        config.llm.model = model
    if api_key:
        config.llm.api_key = api_key
    if base_url:
        config.llm.base_url = base_url
    if template:
        config.template.default = template
    if output:
        config.output.directory = output

    # 执行
    _run(url, config, verbose=not quiet)


@cli.command("list-templates")
def list_templates_cmd():
    """列出所有可用的 LaTeX 模板"""
    result = list_templates_tool.invoke({})
    console.print(result)


@cli.command("config")
@click.option("--config-file", "-c", help="配置文件路径", default=None)
def show_config_cmd(config_file):
    """显示当前配置"""
    config = load_config(config_file)
    console.print(Panel.fit(
        f"[bold]LLM Provider:[/] {config.llm.provider}\n"
        f"[bold]Model:[/] {config.llm.model}\n"
        f"[bold]Temperature:[/] {config.llm.temperature}\n"
        f"[bold]Template:[/] {config.template.default}\n"
        f"[bold]Output Dir:[/] {config.output.directory}\n"
        f"[bold]Compiler:[/] {config.compiler.engine} (×{config.compiler.runs})",
        title="📋 当前配置"
    ))


def _run(url: str, config: AppConfig, verbose: bool = True):
    """执行论文解读"""
    console.print(BANNER)

    try:
        # 创建 LLM
        console.print(f"[bold blue]🤖 LLM:[/] {config.llm.provider} / {config.llm.model}")
        llm = create_llm(
            provider=config.llm.provider,
            model=config.llm.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

        # 创建 Agent
        console.print(f"[bold blue]📄 模板:[/] {config.template.default}")
        agent = create_scholar_agent(
            llm=llm,
            template_name=config.template.default,
        )

        # 运行 Agent
        console.print(f"[bold blue]🔗 论文:[/] {url}\n")
        run_agent(
            agent=agent,
            arxiv_url=url,
            template_name=config.template.default,
            verbose=verbose,
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]❌ 错误:[/] {e}")
        import traceback
        if verbose:
            traceback.print_exc()
        sys.exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
