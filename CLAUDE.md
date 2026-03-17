# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Paper Granny (论文奶奶) is an AI agent that downloads arXiv paper LaTeX source code, performs deep reading comprehension, and generates Chinese interpretation report PDFs. It uses a LangGraph ReAct agent with 7 specialized tools.

## Commands

### Run Web Server
```bash
python -m uvicorn src.server:app --reload --port 8000
```

### Run CLI
```bash
python -m src.main --url <arxiv_url_or_id>
python -m src.main --url 2603.03251 -p deepseek -m deepseek-chat
python -m src.main list-templates
python -m src.main config
```

### Install Dependencies
```bash
pip install -r requirements.txt
```
Requires Python 3.10+ and XeLaTeX (TeX Live or MacTeX).

## Architecture

**Agent loop**: `src/main.py` (CLI) or `src/server.py` (FastAPI+SSE) → `src/agent.py` creates a LangGraph `create_react_agent` → agent autonomously calls tools from `src/tools.py` in a ReAct loop.

**Key design decisions**:
- The system prompt in `src/skills.py` is intentionally minimal — detailed knowledge is injected on-demand via `read_skill()` tool calls that load markdown guides from `skill/*/SKILL.md`.
- All OpenAI-compatible LLM providers (DeepSeek, Kimi, DashScope, SiliconFlow, OpenRouter, Ollama, vLLM) are handled uniformly via `ChatOpenAI` with custom `base_url` in `src/llm_factory.py`. Only Claude uses its native `ChatAnthropic` SDK.
- Config priority: CLI args > env vars > `config.local.yaml` > `config.yaml` > dataclass defaults (in `src/config.py`).

**Tool system** (`src/tools.py`): 7 LangChain `@tool` functions — `run_shell`, `read_file`, `write_file`, `list_dir`, `list_templates`, `read_template`, `read_skill`. All relative paths resolve against project root via `_resolve_path()`.

**Web server** (`src/server.py`): FastAPI app that streams agent events via SSE using `agent.astream_events()`. The frontend is a single `web/index.html` file.

**Output convention**: Papers download to `papers/{arxiv_id}/source/`, reports generate at `papers/{arxiv_id}/report.tex`, compiled with xelatex (2 passes).

## Configuration

- `config.yaml` — default config (checked in)
- `config.local.yaml` — local overrides with API keys (gitignored)
- Environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, etc.

## Adding New LLM Providers

Add an entry to `OPENAI_COMPATIBLE_PROVIDERS` dict in `src/llm_factory.py` and update `get_supported_providers()` if the provider uses the OpenAI-compatible API.

## Adding Templates

Create a subdirectory in `latex_template/` with a `.cls` file of the same name (e.g. `latex_template/MyTemplate/MyTemplate.cls`). The agent auto-discovers them and reports only need `\documentclass{Name}`. First line comment is used as description.