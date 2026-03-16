# Scholar Granny 📖

[English](README.md)

> **arXiv 论文智能解读 Agent** — 基于 LangGraph ReAct 的自主论文分析系统

Scholar Granny 是一个 AI Agent，能够自动下载 arXiv 论文 LaTeX 源码、深度阅读理解、并生成精美的中文解读报告 PDF。

## ✨ 特性

- 🤖 **LangGraph ReAct Agent** — LLM 自主决策，按需调用 7 种工具
- 🌐 **Web UI + CLI** — 精美 Web 界面 & 命令行双入口
- 📡 **SSE 实时流式** — 通过 Server-Sent Events 实时展示 Agent 推理过程
- 🔌 **10+ LLM Provider** — OpenAI / Claude / DeepSeek / Kimi / 通义 / SiliconFlow / OpenRouter / Ollama / vLLM
- 📄 **LaTeX 模板系统** — 可扩展的报告模板，生成精美 PDF（已预置 "Modern Colorful" 模板，开箱即用）
- 🧠 **Skill 子技能系统** — Agent 按需读取技能指南，模块化知识注入
- 🔑 **Web 界面配置 API Key** — 直接在浏览器中配置 API Key、选择 Provider 和模型，无需手动编辑配置文件或环境变量

## 🚀 快速开始

### 📦 安装

```bash
pip install -r requirements.txt
```

### 🔑 配置 API Key

**方式一：通过 Web 界面配置（推荐）**

启动服务器后，在浏览器中即可完成所有配置 — Provider、模型、API Key 等：

```bash
python -m uvicorn src.server:app --reload --port 8000
# 浏览器打开 http://localhost:8000
```

Web 界面提供设置面板，支持：
- 选择 LLM Provider 和模型
- 输入 API Key（支持显示/隐藏切换）
- 设置自定义 Base URL、Temperature、输出语言
- 所有设置自动保存

**方式二：通过环境变量设置**

```bash
export OPENAI_API_KEY="sk-xxx"
# 或
export ANTHROPIC_API_KEY="sk-ant-xxx"
# 或
export DEEPSEEK_API_KEY="sk-xxx"
```

**方式三：通过配置文件**

创建 `config.local.yaml`（已被 `.gitignore` 忽略）覆盖默认配置：

```yaml
llm:
  provider: deepseek
  model: deepseek-chat
  api_key: "sk-xxx"
```

### 💡 使用

**Web 界面（推荐）**

```bash
python -m uvicorn src.server:app --reload --port 8000
# 浏览器打开 http://localhost:8000
```

**命令行**

```bash
# 基本用法
python -m src.main --url https://arxiv.org/abs/2603.03251

# 指定 LLM
python -m src.main --url 2603.03251 -p claude -m claude-sonnet-4-20250514

# 使用 DeepSeek
python -m src.main --url 2603.03251 -p deepseek -m deepseek-chat

# 使用本地 Ollama
python -m src.main --url 2603.03251 -p ollama -m llama3

# 使用 vLLM
python -m src.main --url 2603.03251 -p vllm -m my-model --base-url http://localhost:8000/v1

# 指定模板
python -m src.main --url 2603.03251 -t "Modern Colorful"

# 列出可用模板
python -m src.main list-templates

# 安静模式（不打印推理过程）
python -m src.main --url 2603.03251 -q
```

## 🏗️ 架构

```
用户输入 arXiv URL
        │
        ▼
  ┌─────────────┐
  │  ReAct Agent │◄── System Prompt + SKILL.md
  │  (LLM Brain) │
  └──────┬──────┘
         │ 自主调用
         ▼
  ┌──────────────────────────────────────┐
  │ run_shell     → wget, tar, xelatex  │
  │ read_file     → 阅读 .tex/.bib 源码  │
  │ write_file    → 生成 report.tex      │
  │ list_dir      → 探索目录结构          │
  │ list_templates → 查看可用模板         │
  │ read_template → 获取模板 preamble    │
  │ read_skill    → 按需学习子技能        │
  └──────────────────────────────────────┘
         │
         ▼
   生成 PDF 解读报告
```

## 🔌 支持的 LLM Provider

| Provider | 环境变量 | 默认模型 | 备注 |
|----------|---------|---------|------|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` | |
| Claude | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | Anthropic 原生 SDK |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-chat` | |
| Kimi | `MOONSHOT_API_KEY` | `moonshot-v1-128k` | |
| DashScope (通义) | `DASHSCOPE_API_KEY` | `qwen-plus` | |
| DashScope Coding | `DASHSCOPE_API_KEY` | `qwen-plus` | 编码优化端点 |
| SiliconFlow | `SILICONFLOW_API_KEY` | `Qwen/Qwen3-8B` | |
| OpenRouter | `OPENROUTER_API_KEY` | `google/gemini-2.5-flash` | |
| Ollama | 无需设置 | `llama3` | 本地部署 |
| vLLM | 无需设置 | 自定义 | 需设置 `base_url` |

## 📁 项目结构

```
Paper_Granny/
├── config.yaml                  # 默认配置
├── config.local.yaml            # 本地覆盖配置 (gitignored)
├── requirements.txt             # Python 依赖
├── latex_template/              # LaTeX 模板目录
│   └── Modern Colorful.tex      # 预置模板，开箱即用
├── skill/                       # Agent 子技能指南 (按需读取)
│   ├── arxiv_downloader/SKILL.md
│   ├── latex_reader/SKILL.md
│   ├── paper_interpreter/SKILL.md
│   ├── report_writer/SKILL.md
│   ├── pdf_compiler/SKILL.md
│   └── template_manager/SKILL.md
├── src/
│   ├── main.py                  # CLI 入口
│   ├── server.py                # FastAPI Web 服务器 (SSE)
│   ├── agent.py                 # LangGraph ReAct Agent
│   ├── tools.py                 # 7 个 Agent 工具
│   ├── skills.py                # Skill 加载与注入
│   ├── llm_factory.py           # LLM Provider 工厂
│   └── config.py                # 配置管理
└── web/
    └── index.html               # Web 前端
```

## 🔧 自定义

### 添加模板

将 `.tex` 模板放入 `latex_template/` 目录即可，Agent 自动发现。

## 📝 环境要求

- Python 3.10+
- XeLaTeX（TeX Live 或 MacTeX）
- 中文字体：**无需额外安装**，模板自动检测系统字体
  - macOS：Songti SC / Heiti SC（系统自带）
  - Windows：SimSun / SimHei / Microsoft YaHei（系统自带）
  - Linux：Fandol 字体（TeX Live 自带）

## 📄 License

MIT
