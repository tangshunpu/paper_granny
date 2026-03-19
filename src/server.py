"""
Scholar Granny Web Server

FastAPI 后端，通过 SSE 流式推送 Agent 的推理过程。
"""

import asyncio
import json
import logging
import re
import shutil
import time
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scholar_granny")

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


def _mask_api_key(key: str) -> str:
    """将 API key 脱敏，只保留前3位和后4位。"""
    if not key or len(key) <= 8:
        return "****" if key else ""
    return key[:3] + "..." + key[-4:]


def _is_masked(value: str) -> bool:
    """判断值是否是脱敏后的 key（含 '...' 且长度较短）。"""
    return bool(value) and "..." in value and len(value) <= 11


@app.get("/api/config")
async def get_config():
    """获取当前配置，包含所有已保存的 provider 设置（api_key 脱敏返回）"""
    import yaml as _yaml
    config = load_config()
    project_root = Path(__file__).parent.parent
    local_config_path = project_root / "config.local.yaml"

    # 读取 providers 字典（各 provider 独立存储的 api_key/model/base_url）
    providers_cfg: dict = {}
    if local_config_path.exists():
        try:
            raw = _yaml.safe_load(local_config_path.read_text(encoding="utf-8")) or {}
            providers_cfg = raw.get("providers", {})
        except Exception:
            pass

    # 脱敏所有 api_key
    safe_providers = {}
    for name, pcfg in providers_cfg.items():
        safe_pcfg = dict(pcfg)
        if "api_key" in safe_pcfg:
            safe_pcfg["api_key"] = _mask_api_key(safe_pcfg["api_key"])
        safe_providers[name] = safe_pcfg

    return {
        "provider": config.llm.provider,
        "model": config.llm.model,
        "temperature": config.llm.temperature,
        "template": config.template.default,
        "providers": safe_providers,
    }


@app.post("/api/config")
async def save_config(request: Request):
    """将 Web UI 当前 provider 的设置保存到 config.local.yaml（按 provider 分区存储）"""
    import yaml as _yaml
    body = await request.json()

    project_root = Path(__file__).parent.parent
    local_config_path = project_root / "config.local.yaml"

    # 读取现有 local config
    existing: dict = {}
    if local_config_path.exists():
        try:
            existing = _yaml.safe_load(local_config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            existing = {}

    provider = body.get("provider", "")

    # ── 更新 llm（全局活跃 provider/model/temperature）──
    llm = existing.get("llm", {})
    if provider:
        llm["provider"] = provider
    if body.get("model"):
        llm["model"] = body["model"]
    if body.get("temperature") is not None:
        llm["temperature"] = float(body["temperature"])
    existing["llm"] = llm

    # ── 按 provider 分别存储 api_key / model / base_url ──
    if provider:
        providers = existing.get("providers", {})
        p_cfg = providers.get(provider, {})
        if body.get("api_key") and not _is_masked(body["api_key"]):
            # 只有传入完整新 key 时才更新，脱敏值不覆盖原始 key
            p_cfg["api_key"] = body["api_key"]
        if body.get("model"):
            p_cfg["model"] = body["model"]
        if body.get("base_url"):
            p_cfg["base_url"] = body["base_url"]
        elif "base_url" in p_cfg and not body.get("base_url"):
            p_cfg.pop("base_url", None)
        providers[provider] = p_cfg
        existing["providers"] = providers

    # ── 更新 template ──
    if body.get("template"):
        existing.setdefault("template", {})["default"] = body["template"]

    try:
        local_config_path.write_text(
            _yaml.dump(existing, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
        return {"ok": True, "saved_to": str(local_config_path)}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/providers")
async def get_providers():
    """获取支持的 provider 列表"""
    from .llm_factory import get_supported_providers
    return {"providers": get_supported_providers()}


def _fetch_arxiv_metadata(arxiv_id: str, paper_dir: Path) -> dict:
    """从 arXiv API 获取论文元数据并缓存到 metadata.json。"""
    meta_path = paper_dir / "metadata.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 从 arXiv Atom API 获取
    meta = {"title": "", "abstract": "", "authors": "", "published": ""}
    try:
        import requests
        import xml.etree.ElementTree as ET

        clean_id = arxiv_id.split("v")[0]  # 去除版本号
        resp = requests.get(
            f"https://export.arxiv.org/api/query?id_list={clean_id}&max_results=1",
            timeout=10,
        )
        if resp.status_code == 200:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(resp.text)
            entry = root.find("atom:entry", ns)
            if entry is not None:
                title_el = entry.find("atom:title", ns)
                summary_el = entry.find("atom:summary", ns)
                published_el = entry.find("atom:published", ns)
                authors = entry.findall("atom:author/atom:name", ns)

                meta["title"] = " ".join((title_el.text or "").split()) if title_el is not None else ""
                meta["abstract"] = " ".join((summary_el.text or "").split()) if summary_el is not None else ""
                meta["authors"] = ", ".join(a.text for a in authors[:5])
                if len(authors) > 5:
                    meta["authors"] += f" et al. ({len(authors)})"
                meta["published"] = (published_el.text or "")[:10] if published_el is not None else ""

        # 缓存到文件
        if meta["title"]:
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to fetch arXiv metadata for %s: %s", arxiv_id, e)

    return meta


@app.get("/api/papers")
async def list_papers():
    """列出已生成的论文报告，包含标题、摘要和时间信息"""
    papers_dir = _project_root() / "papers"
    papers = []
    if papers_dir.exists():
        for paper_dir in sorted(papers_dir.iterdir()):
            if paper_dir.is_dir():
                pdf_files = [f for f in paper_dir.glob("*.pdf") if f.name != "original.pdf"]
                arxiv_id = paper_dir.name

                # 获取元数据（title, abstract, authors, published）
                meta = _fetch_arxiv_metadata(arxiv_id, paper_dir)

                # 生成时间：取 PDF 或目录的 mtime
                generated_ts = ""
                if pdf_files:
                    generated_ts = time.strftime(
                        "%Y-%m-%d %H:%M",
                        time.localtime(max(f.stat().st_mtime for f in pdf_files)),
                    )
                elif paper_dir.exists():
                    generated_ts = time.strftime(
                        "%Y-%m-%d %H:%M",
                        time.localtime(paper_dir.stat().st_mtime),
                    )

                papers.append({
                    "arxiv_id": arxiv_id,
                    "has_pdf": len(pdf_files) > 0,
                    "pdf_name": pdf_files[0].name if pdf_files else None,
                    "title": meta.get("title", ""),
                    "abstract": meta.get("abstract", ""),
                    "authors": meta.get("authors", ""),
                    "published": meta.get("published", ""),
                    "generated": generated_ts,
                })
    return {"papers": papers}


@app.get("/api/papers/{arxiv_id}/pdf")
async def download_pdf(arxiv_id: str):
    """下载生成的 PDF（返回最新生成的文件）"""
    papers_dir = _project_root() / "papers" / arxiv_id
    pdf_files = sorted(
        (f for f in papers_dir.glob("*.pdf") if f.name != "original.pdf"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    if pdf_files:
        latest = pdf_files[0]
        return FileResponse(
            str(latest),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=\"{latest.name}\""},
        )
    return JSONResponse({"error": "PDF not found"}, status_code=404)


def _ensure_arxiv_pdf(arxiv_id: str, papers_dir: Path) -> Path | None:
    """确保原始 arXiv PDF 存在，不存在则从 arxiv.org 下载。"""
    original_pdf = papers_dir / "original.pdf"
    if original_pdf.exists():
        return original_pdf
    try:
        import requests as req
        url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        resp = req.get(url, timeout=30, headers={"User-Agent": "PaperGranny/1.0"})
        if resp.status_code == 200 and len(resp.content) > 1000:
            papers_dir.mkdir(parents=True, exist_ok=True)
            original_pdf.write_bytes(resp.content)
            return original_pdf
    except Exception:
        pass
    return None


@app.get("/api/papers/{arxiv_id}/thumbnail")
async def pdf_thumbnail(arxiv_id: str):
    """返回原始论文第一页的缩略图 (PNG)。优先使用原始 arXiv PDF，回退到生成的报告 PDF。"""
    papers_dir = _project_root() / "papers" / arxiv_id
    if not papers_dir.exists():
        return JSONResponse({"error": "Paper not found"}, status_code=404)

    thumb_path = papers_dir / ".thumbnail.png"

    # 优先用原始 PDF，回退到报告 PDF
    source_pdf = _ensure_arxiv_pdf(arxiv_id, papers_dir)
    if source_pdf is None:
        # 回退：使用报告 PDF
        pdf_files = sorted(papers_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        source_pdf = pdf_files[0] if pdf_files else None
    if source_pdf is None:
        return JSONResponse({"error": "No PDF available"}, status_code=404)

    # 使用缓存：如果缩略图比源 PDF 新则直接返回
    if thumb_path.exists() and thumb_path.stat().st_mtime >= source_pdf.stat().st_mtime:
        return FileResponse(str(thumb_path), media_type="image/png")

    try:
        import fitz  # pymupdf
        doc = fitz.open(str(source_pdf))
        page = doc[0]
        # 缩放到 ~300px 宽
        zoom = 300 / page.rect.width
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(thumb_path))
        doc.close()
        return FileResponse(str(thumb_path), media_type="image/png")
    except ImportError:
        return JSONResponse({"error": "pymupdf not installed"}, status_code=501)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/papers/{arxiv_id}")
async def delete_paper(arxiv_id: str):
    """删除指定论文的整个目录（包括源码、报告、PDF）"""
    import shutil
    papers_dir = _project_root() / "papers" / arxiv_id
    if not papers_dir.exists():
        return JSONResponse({"error": "Not found"}, status_code=404)
    shutil.rmtree(papers_dir)
    return {"ok": True, "arxiv_id": arxiv_id}


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
            # Step 0: 检查 xelatex 是否已安装
            if not shutil.which("xelatex"):
                yield _sse_event("error", {
                    "message": (
                        "❌ LaTeX (xelatex) not found!\n\n"
                        "Paper Granny requires XeLaTeX to compile PDF reports.\n\n"
                        "Please install LaTeX first:\n"
                        "  • macOS: install MacTeX (https://tug.org/mactex/)\n"
                        "  • Linux: sudo apt install texlive-xetex  (or texlive-full)\n"
                        "  • Windows: install TeX Live (https://tug.org/texlive/)\n\n"
                        "Then restart the server and try again."
                    )
                })
                return

            # Step 1: 创建 LLM
            logger.info("[SSE] Step 1: 创建 LLM %s/%s", provider, model)
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
            logger.info("[SSE] Step 2: 构建 Agent")
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
                "8. 使用 compile_pdf 编译 PDF\n"
                "9. compile_pdf 成功后：直接输出一段纯文字总结（论文标题 + PDF路径），"
                "不要再调用任何工具，不要用 run_shell echo 汇报——否则会无限循环。\n"
            )

            yield _sse_event("status", {"step": "running", "message": "🚀 Agent 开始工作..."})
            yield _sse_event("task", {"content": task_message})

            # Step 4: 流式运行 Agent
            logger.info("[SSE] Step 4: 开始 astream_events 循环")
            event_count = 0
            last_event_time = time.time()
            last_event_kind = ""

            async for event in agent.astream_events(
                {"messages": [HumanMessage(content=task_message)]},
                version="v2",
                config={"recursion_limit": 150},
            ):
                kind = event["event"]
                event_count += 1
                now = time.time()
                gap = now - last_event_time

                # 每 50 个事件 或 间隔超过 5 秒时打日志
                if event_count % 50 == 0 or gap > 5:
                    logger.info(
                        "[SSE] event #%d kind=%s (gap=%.1fs, prev=%s)",
                        event_count, kind, gap, last_event_kind,
                    )

                last_event_time = now
                last_event_kind = kind

                if kind == "on_tool_start":
                    tool_name = event["name"]
                    tool_input = event.get("data", {}).get("input", {})
                    display = _format_tool_call(tool_name, tool_input)
                    logger.info("[SSE] TOOL START: %s → %s", tool_name, display[:200])
                    yield _sse_event("tool_start", {
                        "tool": tool_name,
                        "input": display,
                    })

                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    output = str(event.get("data", {}).get("output", ""))
                    logger.info("[SSE] TOOL END: %s (output len=%d)", tool_name, len(output))
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
            logger.info("[SSE] astream_events 循环结束，共 %d 个事件", event_count)
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
            logger.error("[SSE] 异常: %s", e)
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
        pdfs = sorted(papers_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if pdfs:
            return str(pdfs[0])
    return None
