"""
Scholar Granny Web Server

FastAPI 后端，通过 SSE 流式推送 Agent 的推理过程。
"""

import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from .config import load_config
from .llm_factory import create_llm
from .tools import _project_root

app = FastAPI(title="Scholar Granny", version="0.2.0")

# 静态文件
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")


# ─── API 路由 ─────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    index_file = web_dir / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/api/templates")
async def get_templates():
    """获取可用模板列表"""
    template_dir = _project_root() / "latex_template"
    templates = []
    if template_dir.exists():
        for sub in sorted(template_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            cls_file = sub / f"{sub.name}.cls"
            if not cls_file.exists():
                cls_files = list(sub.glob("*.cls"))
                if not cls_files:
                    continue
                cls_file = cls_files[0]
            try:
                first_line = cls_file.read_text(encoding="utf-8").split("\n")[0]
                desc = first_line.lstrip("% ").strip() if first_line.startswith("%") else ""
            except Exception:
                desc = ""
            templates.append({
                "name": cls_file.stem,
                "description": desc,
                "size_kb": round(cls_file.stat().st_size / 1024, 1),
            })
    return {"templates": templates}


@app.get("/api/config")
async def get_config():
    """获取当前配置"""
    config = load_config()
    return {
        "provider": config.llm.provider,
        "model": config.llm.model,
        "temperature": config.llm.temperature,
        "template": config.template.default,
    }


@app.get("/api/providers")
async def get_providers():
    """获取支持的 provider 列表"""
    from .llm_factory import get_supported_providers
    return {"providers": get_supported_providers()}


@app.get("/api/papers")
async def list_papers():
    """列出已生成的论文报告"""
    papers_dir = _project_root() / "papers"
    papers = []
    if papers_dir.exists():
        for paper_dir in sorted(papers_dir.iterdir()):
            if paper_dir.is_dir():
                pdf_files = list(paper_dir.glob("*.pdf"))
                papers.append({
                    "arxiv_id": paper_dir.name,
                    "has_pdf": len(pdf_files) > 0,
                    "pdf_name": pdf_files[0].name if pdf_files else None,
                })
    return {"papers": papers}


@app.get("/api/papers/{arxiv_id}/pdf")
async def download_pdf(arxiv_id: str):
    """下载生成的 PDF"""
    papers_dir = _project_root() / "papers" / arxiv_id
    pdf_files = list(papers_dir.glob("*.pdf"))
    if pdf_files:
        return FileResponse(
            str(pdf_files[0]),
            media_type="application/pdf",
            filename=pdf_files[0].name,
        )
    return JSONResponse({"error": "PDF not found"}, status_code=404)


@app.post("/api/run")
async def run_agent_sse(request: Request):
    """
    运行 Agent 解读论文，通过 SSE 流式推送进度。
    
    Request body:
    {
        "arxiv_url": "https://arxiv.org/abs/2603.03251",
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "sk-xxx",
        "base_url": null,
        "temperature": 0.3,
        "template": "ModernColorful",
        "language": "中文"
    }
    """
    body = await request.json()

    arxiv_url = body.get("arxiv_url", "")
    provider = body.get("provider", "openai")
    model = body.get("model", "gpt-4o")
    api_key = body.get("api_key", "")
    base_url = body.get("base_url") or None
    temperature = float(body.get("temperature", 0.3))
    template_name = body.get("template", "ModernColorful")
    language = body.get("language", "中文")

    if not arxiv_url:
        return JSONResponse({"error": "arxiv_url is required"}, status_code=400)

    async def event_generator():
        try:
            # Step 1: 创建 LLM
            yield _sse_event("status", {"step": "init", "message": f"🤖 初始化 LLM: {provider}/{model}"})
            await asyncio.sleep(0.1)

            llm = create_llm(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
            )

            # Step 2: 构建 Agent
            yield _sse_event("status", {"step": "agent", "message": "🧠 构建 ReAct Agent..."})
            await asyncio.sleep(0.1)

            from langchain_core.messages import HumanMessage
            from .agent import create_scholar_agent

            agent = create_scholar_agent(
                llm=llm,
                template_name=template_name,
                language=language,
            )

            # Step 3: 构建任务消息
            task_message = (
                f"请解读这篇 arXiv 论文: {arxiv_url}\n"
                f"使用 LaTeX 模板: {template_name}\n"
                f"报告语言: {language}\n\n"
                "请按以下步骤自主工作:\n"
                "1. 使用 download_paper 工具下载论文源码（已下载过会自动跳过）\n"
                "2. 探索源码目录结构，找到主 tex 文件\n"
                "3. 深度阅读论文源码（包括所有 \\input 引用的文件）\n"
                "4. 读取 paper_interpreter 技能指南，学习解读方法\n"
                "5. 读取模板 preamble，了解可用的盒子和命令\n"
                "6. 读取 report_writer 技能指南，学习报告写作规范\n"
                "7. 生成完整的 LaTeX 解读报告 (使用模板的 preamble + 你的解读内容)\n"
                "8. 编译 PDF（xelatex 运行两次）\n"
                "9. 报告最终结果\n"
            )

            yield _sse_event("status", {"step": "running", "message": "🚀 Agent 开始工作..."})
            yield _sse_event("task", {"content": task_message})

            # Step 4: 流式运行 Agent
            async for event in agent.astream_events(
                {"messages": [HumanMessage(content=task_message)]},
                version="v2",
                config={"recursion_limit": 150},
            ):
                kind = event["event"]

                if kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event.get("data", {}).get("input", {})
                    display = _format_tool_call(tool_name, tool_input)
                    yield _sse_event("tool_start", {
                        "tool": tool_name,
                        "input": display,
                    })

                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    output = str(event.get("data", {}).get("output", ""))
                    # 截断过长的输出
                    if len(output) > 2000:
                        output = output[:2000] + f"\n... (截断，共 {len(output)} 字符)"
                    yield _sse_event("tool_end", {
                        "tool": tool_name,
                        "output": output,
                    })

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        # 普通文本流（agent 的推理过程）
                        if hasattr(chunk, "content") and chunk.content:
                            yield _sse_event("thinking", {"content": chunk.content})
                        # tool call 流（生成 write_file 等工具参数时的流式输出）
                        if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                            for tc_chunk in chunk.tool_call_chunks:
                                args_text = tc_chunk.get("args", "")
                                tool_name = tc_chunk.get("name", "")
                                if args_text:
                                    yield _sse_event("tool_streaming", {
                                        "tool": tool_name or "",
                                        "content": args_text,
                                    })

            # 完成
            # 检查是否生成了 PDF
            arxiv_id = _extract_arxiv_id(arxiv_url)
            pdf_path = _find_pdf(arxiv_id)

            yield _sse_event("complete", {
                "message": "✅ 论文解读完成！",
                "arxiv_id": arxiv_id,
                "has_pdf": pdf_path is not None,
                "pdf_url": f"/api/papers/{arxiv_id}/pdf" if pdf_path else None,
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield _sse_event("error", {"message": str(e)})

    return EventSourceResponse(event_generator())


# ─── Helper functions ─────────────────────────────────────────


def _sse_event(event_type: str, data: dict) -> dict:
    return {"event": event_type, "data": json.dumps(data, ensure_ascii=False)}


def _format_tool_call(tool_name: str, tool_input: dict) -> str:
    if tool_name == "run_shell":
        return f"$ {tool_input.get('command', '')}"
    elif tool_name == "read_file":
        return f"📖 {tool_input.get('path', '')}"
    elif tool_name == "write_file":
        return f"✏️ {tool_input.get('path', '')}"
    elif tool_name == "edit_file":
        edits = tool_input.get('edits', [])
        return f"📝 {tool_input.get('path', '')} ({len(edits)} edits)"
    elif tool_name == "list_dir":
        return f"📂 {tool_input.get('path', '.')}"
    elif tool_name == "read_skill":
        return f"📖 skill/{tool_input.get('skill_name', '')}"
    elif tool_name == "read_template":
        return f"📄 template: {tool_input.get('template_name', '')}"
    elif tool_name == "list_templates":
        return "📋 listing templates"
    elif tool_name == "compile_pdf":
        return f"🔨 compiling {tool_input.get('tex_path', '')}"
    elif tool_name == "get_image_info":
        return f"📸 scanning images in {tool_input.get('path', '')}"
    return str(tool_input)


def _extract_arxiv_id(url: str) -> str:
    patterns = [
        r"arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)",
        r"arxiv\.org/pdf/(\d{4}\.\d{4,5}(?:v\d+)?)",
        r"^(\d{4}\.\d{4,5}(?:v\d+)?)$",
        r"arXiv:(\d{4}\.\d{4,5}(?:v\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url.strip(), re.IGNORECASE)
        if match:
            return match.group(1)
    return url.strip().split("/")[-1]


def _find_pdf(arxiv_id: str) -> Optional[str]:
    papers_dir = _project_root() / "papers" / arxiv_id
    if papers_dir.exists():
        pdfs = list(papers_dir.glob("*.pdf"))
        if pdfs:
            return str(pdfs[0])
    return None
