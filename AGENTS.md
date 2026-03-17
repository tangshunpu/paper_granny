# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `src/`. Use `src/main.py` for the CLI entry point, `src/server.py` for the FastAPI web server, `src/agent.py` for LangGraph agent orchestration, and `src/tools.py`, `src/skills.py`, and `src/config.py` for tool loading and configuration. Web assets are in `web/`, LaTeX report templates are in `latex_template/`, skill guides are in `skill/`, and generated outputs are typically written under `papers/`. Example PDFs and branding assets live in `example/` and `figure/`.

## Build, Test, and Development Commands
Install dependencies with `pip install -r requirements.txt`.
Run the web app locally with `python -m uvicorn src.server:app --reload --port 8000`.
Run the CLI against an arXiv paper with `python -m src.main --url 2603.03251`.
Inspect available LaTeX templates with `python -m src.main list-templates`.
Review effective configuration with `python -m src.main config`.
This project also requires XeLaTeX on your machine for PDF generation.

## Coding Style & Naming Conventions
Follow existing Python style: 4-space indentation, `snake_case` for functions and variables, `PascalCase` for dataclasses, and concise module docstrings. Keep new modules under `src/` focused on one responsibility. Prefer standard library types and explicit imports over wildcard imports. There is no repository-enforced formatter yet, so keep changes consistent with surrounding code and avoid unnecessary rewrites.

## Testing Guidelines
There is no committed automated test suite yet. For code changes, validate both entry points you touch: run the CLI for a sample arXiv ID and start the FastAPI server to confirm the affected route or UI flow still works. If you add tests, prefer `pytest`, place them in `tests/`, and name files `test_<module>.py` to match common Python discovery.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commit-style subjects such as `feat: add example reports` and `feat: 添加专用 compile_pdf 工具`. Continue using prefixes like `feat:`, `fix:`, and `docs:` with a short imperative summary. Pull requests should describe user-visible behavior changes, list verification steps, link related issues, and include screenshots for `web/` UI updates.

## Security & Configuration Tips
Do not commit API keys or local overrides. Store secrets in environment variables or `config.local.yaml`, which is intended for machine-local configuration. Treat generated PDFs and downloaded paper sources as build artifacts unless the change explicitly updates examples.
