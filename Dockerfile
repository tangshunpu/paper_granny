# =============================================================
# Paper Granny (论文奶奶) - Docker 镜像
# 包含完整 TeX Live + 中文字体环境
# =============================================================
FROM python:3.12-slim AS base

# 元信息
LABEL maintainer="Paper Granny"
LABEL description="AI agent for arXiv paper reading and Chinese report generation"

# 避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ---------- 系统依赖 + TeX Live + 中文字体 ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    # TeX Live (XeLaTeX + 中文支持)
    texlive-xetex \
    texlive-lang-chinese \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-latex-extra \
    # 中文字体
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    # 工具
    wget \
    tar \
    gzip \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# ---------- Python 依赖 ----------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- 应用代码 ----------
COPY . .

# ---------- 数据卷 ----------
# papers 目录用于持久化输出
VOLUME ["/app/papers"]

# ---------- 环境变量 ----------
# 用户通过 -e 或 .env 传入 API Key
# ENV OPENAI_API_KEY=""
# ENV DEEPSEEK_API_KEY=""

EXPOSE 8000

# ---------- 健康检查 ----------
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# ---------- 启动 ----------
CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
