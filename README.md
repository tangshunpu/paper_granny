<p align="center">
  <img src="figure/logo.png" alt="Scholar Granny Logo" width="200">
</p>

# Paper Granny 📖

[中文文档](README_CN.md)

> **arXiv Paper Interpretation Agent** — Autonomous paper analysis system powered by LangGraph ReAct

Paper Granny is an AI Agent that automatically downloads arXiv paper LaTeX source code, performs deep reading comprehension, and generates beautifully formatted interpretation report PDFs.

## ✨ Features

- 🤖 **LangGraph ReAct Agent** — LLM autonomous decision-making with 7 specialized tools
- 🌐 **Web UI + CLI** — Beautiful web interface & command-line dual entry points
- 📡 **SSE Real-time Streaming** — Live display of Agent reasoning process via Server-Sent Events
- 🔌 **10+ LLM Providers** — OpenAI / Claude / DeepSeek / Kimi / DashScope / SiliconFlow / OpenRouter / Ollama / vLLM
- 📄 **LaTeX Template System** — Extensible report templates for beautiful PDF generation (a "Modern Colorful" template is pre-built and ready to use)
- 🧠 **Skill Sub-system** — Agent reads skill guides on demand for modular knowledge injection
- 🔑 **Web-based API Key Configuration** — Configure API keys, select providers and models directly from the web UI — no need to edit config files or environment variables

## 📑 Model Recommendation
| Provider | Model | Price | Rating | Example |
|----------|------|:-----:|:------:|--------|
| OpenAI | `gpt-5.4` | 💰💰💰 | ⭐⭐⭐⭐⭐ | [Gated Attention for Large Language Models: Nonlinearity, Sparsity, and Attention-Sink-Free](example/GA.pdf) |
| DashScope | `qwen3.5-plus` | 💰 | ⭐⭐⭐⭐ | [Language Models are Few-Shot Learners](example/Language_Models_are_Few-Shot_Learners.pdf) |
| DashScope | `glm-5` | 💰 | ⭐⭐⭐⭐ | [Deep Residual Learning for Image Recognition (Chinese)](example/Deep_Residual_Learning_for_Image_Recognition.pdf) |
| Google | `gemini-3-flash-preview` | 🆓  | ⭐⭐⭐ | [Denoising Diffusion Probabilistic Models](example/ddpm.pdf) |
| Local | `qwen3.5-35b-a3b-4bit` | 🆓 | ⭐⭐⭐ | [ReAct: Synergizing Reasoning and Acting in Language Models](example/ReAct.pdf) |
| OpenAI | `gpt-5-mini` | 💰 | ⭐ | [Attention Is All You Need](example/Attention_Is_All_You_Need.pdf) |
| OpenAI | `gpt-5.3-codex` | 💰💰💰 | ❌ | Bug |
| OpenRouter | `claude-opus-4.6` | 💰💰💰💰💰💰 | ❌ | Bug |

> We recommend using 2026 latest models such as GPT-5.4, Claude 4.5, DeepSeek V3, Qwen 3.5, GLM-5, etc. These models perform significantly better on Agent tasks. Older models often fail to accurately locate LaTeX compilation errors.

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
├── example/                     # Example report PDFs
├── config.yaml                  # Default configuration
├── config.local.yaml            # Local override config (gitignored)
├── requirements.txt             # Python dependencies
├── latex_template/              # LaTeX template directory
│   └── ModernColorful/          # Pre-built template (recommended)
│       ├── ModernColorful.cls   # Template class file
│       └── Modern Colorful.tex  # Example document
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

Create a subdirectory in `latex_template/` with a `.cls` file of the same name (e.g. `latex_template/MyTemplate/MyTemplate.cls`). The Agent will auto-discover it. Reports only need `\documentclass{MyTemplate}` to use the template.

## 📝 Requirements

- Python 3.10+
- XeLaTeX (TeX Live or MacTeX)

## 📄 License

MIT
