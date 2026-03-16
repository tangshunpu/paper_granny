<p align="center">
  <img src="figure/logo.png" alt="Scholar Granny Logo" width="200">
</p>

# Paper Granny 📖

[中文文档](README_CN.md)

> **arXiv Paper Interpretation Agent** — Autonomous paper analysis system powered by LangGraph ReAct

Scholar Granny is an AI Agent that automatically downloads arXiv paper LaTeX source code, performs deep reading comprehension, and generates beautifully formatted Chinese interpretation report PDFs.

## ✨ Features

- 🤖 **LangGraph ReAct Agent** — LLM autonomous decision-making with 7 specialized tools
- 🌐 **Web UI + CLI** — Beautiful web interface & command-line dual entry points
- 📡 **SSE Real-time Streaming** — Live display of Agent reasoning process via Server-Sent Events
- 🔌 **10+ LLM Providers** — OpenAI / Claude / DeepSeek / Kimi / DashScope / SiliconFlow / OpenRouter / Ollama / vLLM
- 📄 **LaTeX Template System** — Extensible report templates for beautiful PDF generation (a "Modern Colorful" template is pre-built and ready to use)
- 🧠 **Skill Sub-system** — Agent reads skill guides on demand for modular knowledge injection
- 🔑 **Web-based API Key Configuration** — Configure API keys, select providers and models directly from the web UI — no need to edit config files or environment variables

## 🚀 Quick Start

### 📦 Installation

```bash
git clone https://github.com/tangshunpu/paper_granny.git
cd paper_granny
pip install -r requirements.txt
```

### 🔑 Configure API Key

**Option 1: Via Web UI (Recommended)**

Start the server and configure everything from the browser — provider, model, API key, and more:

```bash
python -m uvicorn src.server:app --reload --port 8000
# Open http://localhost:8000 in your browser
```

The web interface provides a settings panel where you can:
- Select your LLM provider and model
- Enter your API key (with show/hide toggle)
- Set custom base URL, temperature, and output language
- All settings are auto-saved

**Option 2: Via Environment Variables**

```bash
export OPENAI_API_KEY="sk-xxx"
# or
export ANTHROPIC_API_KEY="sk-ant-xxx"
# or
export DEEPSEEK_API_KEY="sk-xxx"
```

**Option 3: Via Config File**

Create `config.local.yaml` (git-ignored) to override defaults:

```yaml
llm:
  provider: deepseek
  model: deepseek-chat
  api_key: "sk-xxx"
```

### 💡 Usage

**Web UI (Recommended)**

```bash
python -m uvicorn src.server:app --reload --port 8000
# Open http://localhost:8000
```

**Command Line**

```bash
# Basic usage
python -m src.main --url https://arxiv.org/abs/2603.03251

# Specify LLM
python -m src.main --url 2603.03251 -p claude -m claude-sonnet-4-20250514

# Use DeepSeek
python -m src.main --url 2603.03251 -p deepseek -m deepseek-chat

# Use local Ollama
python -m src.main --url 2603.03251 -p ollama -m llama3

# Use vLLM
python -m src.main --url 2603.03251 -p vllm -m my-model --base-url http://localhost:8000/v1

# Specify template
python -m src.main --url 2603.03251 -t "Modern Colorful"

# List available templates
python -m src.main list-templates

# Quiet mode (no reasoning output)
python -m src.main --url 2603.03251 -q
```

## 🏗️ Architecture

```
User inputs arXiv URL
        |
        v
  +---------------+
  |  ReAct Agent  |<-- System Prompt + SKILL.md
  |  (LLM Brain)  |
  +-------+-------+
          | Autonomous calls
          v
  +--------------------------------------+
  | run_shell     -> wget, tar, xelatex |
  | read_file     -> Read .tex/.bib src  |
  | write_file    -> Generate report.tex |
  | list_dir      -> Explore directory   |
  | list_templates -> View templates     |
  | read_template -> Get template        |
  | read_skill    -> Load skill guide    |
  +--------------------------------------+
          |
          v
   Generated PDF Report
```

## 🔌 Supported LLM Providers

| Provider | Environment Variable | Default Model | Notes |
|----------|---------------------|---------------|-------|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` | |
| Claude | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | Anthropic native SDK |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` | |
| Kimi | `MOONSHOT_API_KEY` | `moonshot-v1-128k` | |
| DashScope | `DASHSCOPE_API_KEY` | `qwen-plus` | |
| DashScope Coding | `DASHSCOPE_API_KEY` | `qwen-plus` | Coding-optimized endpoint |
| SiliconFlow | `SILICONFLOW_API_KEY` | `Qwen/Qwen3-8B` | |
| OpenRouter | `OPENROUTER_API_KEY` | `google/gemini-2.5-flash` | |
| Ollama | Not required | `llama3` | Local deployment |
| vLLM | Not required | Custom | Requires `base_url` |

## 📁 Project Structure

```
Paper_Granny/
├── config.yaml                  # Default configuration
├── config.local.yaml            # Local override config (gitignored)
├── requirements.txt             # Python dependencies
├── latex_template/              # LaTeX template directory
│   └── Modern Colorful.tex      # Pre-built template, ready to use
├── skill/                       # Agent skill guides (loaded on demand)
│   ├── arxiv_downloader/SKILL.md
│   ├── latex_reader/SKILL.md
│   ├── paper_interpreter/SKILL.md
│   ├── report_writer/SKILL.md
│   ├── pdf_compiler/SKILL.md
│   └── template_manager/SKILL.md
├── src/
│   ├── main.py                  # CLI entry point
│   ├── server.py                # FastAPI Web server (SSE)
│   ├── agent.py                 # LangGraph ReAct Agent
│   ├── tools.py                 # 7 Agent tools
│   ├── skills.py                # Skill loading & injection
│   ├── llm_factory.py           # LLM Provider factory
│   └── config.py                # Configuration management
└── web/
    └── index.html               # Web frontend
```

## 🔧 Customization

### Adding Templates

Place `.tex` template files in the `latex_template/` directory — the Agent will auto-discover them.

## 📝 Requirements

- Python 3.10+
- XeLaTeX (TeX Live or MacTeX)
- Chinese fonts: **No extra installation needed** — templates auto-detect system fonts
  - macOS: Songti SC / Heiti SC (built-in)
  - Windows: SimSun / SimHei / Microsoft YaHei (built-in)
  - Linux: Fandol fonts (included in TeX Live)

## 📄 License

MIT
