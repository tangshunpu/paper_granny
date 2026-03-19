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

| Rec | Provider   | Model                    | Doc | Code | Price |
|-----|------------|--------------------------|-----|------|-------|
| ⭐⭐⭐⭐⭐ | OpenRouter | `mimo-v2-pro`            | A  | A+   | 💰💰     |
| ⭐⭐⭐⭐ | OpenAI     | `gpt-5.4-mini`           | A   | A+    | 💰💰 |
| ⭐⭐⭐⭐ | OpenAI     | `gpt-5.4`                | A+  | A+   | 💰💰💰💰 |
| ⭐⭐⭐⭐  | DashScope  | `glm-5`                  | A   | A    | 💰       |
| ⭐⭐⭐⭐  | OpenRouter | `mimo-v2-omni`           | A   | A    | 💰       |
| ⭐⭐⭐  | OpenRouter | `minimax-m2.7`           | A   | B    | 💰       |
| ⭐⭐⭐   | OpenRouter | `deepseek-v3.2`          | A   | B    | 💰       |
| ⭐⭐⭐  | DashScope  | `qwen3.5-plus`           | B   | A    | 💰       |
| ⭐⭐⭐   | Google     | `gemini-3-flash`         | B   | B    | 🆓       |
| ⭐⭐    | Local      | `qwen3.5-35b-a3b`        | B   | A    | 🆓       |
| ⭐     | OpenAI     | `gpt-5.4-nano`           | B   | B    | 💰💰   |
| ⭐     | OpenAI     | `gpt-5-mini`             | C   | B    | 💰💰💰   |
| ❌     | NVIDIA     | `nemotron-3-super`       | —   | F    | 💰       |
| 🔧     | OpenAI     | `gpt-5.3-codex`          | -   | -    | 💰💰💰💰 |
| 🔧     | OpenRouter | `claude-opus-4.6`        | -  | -    | 💰💰💰💰💰💰 |

> We recommend using the latest 2026 models such as GPT-5.4, Claude 4.5, DeepSeek V3, Qwen 3.5, and GLM-5, as they demonstrate significantly better performance on agent-based tasks.

> In our evaluation, Code Reliability specifically measures a model’s ability to correctly compile and debug Latex code. Models with high scores can typically generate executable outputs without requiring iterative fixes, whereas older models often fail to accurately locate and resolve compilation errors.

## 📄 Example Reports

| Paper                                                       | Model                     | PDF   |
|-------------------------------------------------------------|--------------------------|-------|
| Gated Attention for Large Language Models                   | `gpt-5.4`                | [PDF](example/GA.pdf) |
| Language Models are Few-Shot Learners                       | `qwen3.5-plus`           | [PDF](example/Language_Models_are_Few-Shot_Learners.pdf) |
| Deep Residual Learning for Image Recognition (Chinese)      | `glm-5`                  | [PDF](example/Deep_Residual_Learning_for_Image_Recognition.pdf) |
| Denoising Diffusion Probabilistic Models                    | `gemini-3-flash-preview` | [PDF](example/ddpm.pdf) |
| ReAct: Synergizing Reasoning and Acting in Language Models  | `qwen3.5-35b-a3b-4bit`  | [PDF](example/ReAct.pdf) |
| Attention Is All You Need                                   | `gpt-5-mini`             | [PDF](example/Attention_Is_All_You_Need.pdf) |

## 🚀 Quick Start

### ⚡ One-Click Deployment

**One command to install everything** (Python, XeLaTeX, Chinese fonts, dependencies) and start as a background service:

```bash
curl -fsSL https://raw.githubusercontent.com/tangshunpu/paper_granny/main/deploy.sh | bash
```

or with `wget`:

```bash
wget -qO- https://raw.githubusercontent.com/tangshunpu/paper_granny/main/deploy.sh | bash
```

The script auto-detects your platform (macOS / Ubuntu / Debian / CentOS / Fedora / Arch), installs all dependencies, and registers a **systemd service** (Linux) or **launchd agent** (macOS) for background persistence.

After deployment, visit `http://localhost:8000` to start using it.

> **Custom install path:** `INSTALL_DIR=/opt/paper_granny bash deploy.sh`
> **Custom port:** `PORT=9000 bash deploy.sh`

### 🐳 Docker Deployment

```bash
git clone https://github.com/tangshunpu/paper_granny.git && cd paper_granny
cp .env.example .env   # Edit .env to add your API key
docker compose up -d
# Visit http://localhost:8000
```

The Docker image comes with TeX Live + XeLaTeX + Chinese fonts pre-installed. The `papers/` directory is mounted for persistent output.

### 📦 Manual Installation

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
| DashScope | `DASHSCOPE_API_KEY` | `qwen3.5-plus` | |
| DashScope Coding | `DASHSCOPE_API_KEY` | `qwen3.5-plus` | |
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
