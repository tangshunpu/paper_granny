"""
LLM Provider 工厂

创建 LangChain ChatModel 实例。
支持 OpenAI / Claude / Gemini / OpenRouter / Kimi / DashScope / DeepSeek / SiliconFlow / Ollama / vLLM。

OpenRouter、Kimi、DashScope、DeepSeek、SiliconFlow 等均为 OpenAI 兼容 API，
统一通过 ChatOpenAI + 自定义 base_url 实现，无需额外 SDK。
"""

import os
from typing import Optional

from langchain_core.language_models import BaseChatModel


# ─── Provider 预设 ────────────────────────────────────────────
# 所有 OpenAI 兼容的 provider 统一注册在此处。
# 每个 provider 包含: base_url, env_key(环境变量名), default_model
OPENAI_COMPATIBLE_PROVIDERS = {
    "openai": {
        "base_url": None,  # 使用 SDK 默认值
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-5.4-mini",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "xiaomi/mimo-v2-pro",
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "env_key": "MOONSHOT_API_KEY",
        "default_model": "moonshot-v1-128k",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "DASHSCOPE_API_KEY",
        "default_model": "qwen3.5-plus",
    },
    "dashscope-coding": {
        "base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "env_key": "DASHSCOPE_API_KEY",
        "default_model": "qwen3.5-plus",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-v3.2",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "env_key": "SILICONFLOW_API_KEY",
        "default_model": "Qwen/Qwen3-8B",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "env_key": None,
        "default_model": "llama3",
        "default_api_key": "ollama",
    },
    "vllm": {
        "base_url": None,  # 必须由用户提供
        "env_key": None,
        "default_model": "",
        "default_api_key": "EMPTY",
    },
}


def get_supported_providers() -> list[dict]:
    """
    返回所有支持的 provider 列表，供 API / 前端使用。
    """
    result = []
    for name, cfg in OPENAI_COMPATIBLE_PROVIDERS.items():
        result.append({
            "name": name,
            "default_model": cfg["default_model"],
            "base_url": cfg.get("base_url") or "",
            "needs_api_key": name not in ("ollama",),
        })
    # 加上 Claude (非 OpenAI 兼容)
    result.append({
        "name": "claude",
        "default_model": "claude-sonnet-4-20250514",
        "base_url": "",
        "needs_api_key": True,
    })
    # 加上 Gemini (非 OpenAI 兼容)
    result.append({
        "name": "gemini",
        "default_model": "gemini-3-flash",
        "base_url": "",
        "needs_api_key": True,
    })
    return result


def create_llm(
    provider: str,
    model: str,
    api_key: str = "",
    base_url: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 16384,
) -> BaseChatModel:
    """
    根据 provider 名称创建 LangChain ChatModel。

    Args:
        provider: 提供商名称
        model: 模型名称
        api_key: API key (也可通过环境变量)
        base_url: 自定义 API 地址 (覆盖 provider 默认值)
        temperature: 生成温度
        max_tokens: 最大 token 数

    Returns:
        LangChain BaseChatModel 实例
    """
    provider = provider.lower()

    # ── Claude (Anthropic 原生 SDK) ──
    if provider == "claude":
        from langchain_anthropic import ChatAnthropic
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        return ChatAnthropic(
            model=model,
            api_key=key,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ── Gemini (Google GenAI 原生 SDK) ──
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=key,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    # ── 所有 OpenAI 兼容 provider ──
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        from langchain_openai import ChatOpenAI
        preset = OPENAI_COMPATIBLE_PROVIDERS[provider]

        # API Key: 参数 > 环境变量 > 默认值
        key = api_key
        if not key and preset.get("env_key"):
            key = os.environ.get(preset["env_key"], "")
        if not key:
            key = preset.get("default_api_key", "")

        # Base URL: 参数 > preset 默认值
        url = base_url or preset.get("base_url")

        # vLLM 必须提供 base_url
        if provider == "vllm" and not url:
            raise ValueError("vLLM provider 需要设置 base_url")

        # 自动补全 /v1 后缀（OpenAI 兼容接口标准路径）
        # 避免用户填写 https://host 而忘记写 /v1 导致请求被拦截
        if url and not url.rstrip("/").endswith("/v1"):
            url = url.rstrip("/") + "/v1"

        kwargs = {
            "model": model,
            "api_key": key,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": 300,       # 5 分钟超时，适配 Agent 长时间流式调用
            "max_retries": 3,     # 遇到瞬时错误（连接中断、5xx）自动重试 3 次
        }
        if url:
            kwargs["base_url"] = url

        # ── 中转站兼容：覆盖 openai SDK 默认的 User-Agent ──
        # 部分中转站/反向代理 WAF 会专门拦截 "User-Agent: OpenAI/Python"。
        # openai SDK 会在 headers 之上强制写入自己的 UA，
        # 必须用 httpx event_hooks 在请求发出前最后一刻修改，才能真正覆盖。
        # 仅对自定义 base_url（非 OpenAI 官方）生效。
        if url and "api.openai.com" not in url:
            import httpx

            # 同步客户端用同步函数
            def _override_ua_sync(request: httpx.Request) -> None:
                request.headers["user-agent"] = "python-httpx/0.27.0"

            # 异步客户端必须用 async 函数，否则 httpx 异步路径会 Connection error
            async def _override_ua_async(request: httpx.Request) -> None:
                request.headers["user-agent"] = "python-httpx/0.27.0"

            kwargs["http_client"] = httpx.Client(
                event_hooks={"request": [_override_ua_sync]},
                timeout=httpx.Timeout(300.0),
            )
            kwargs["http_async_client"] = httpx.AsyncClient(
                event_hooks={"request": [_override_ua_async]},
                timeout=httpx.Timeout(300.0),
            )

        return ChatOpenAI(**kwargs)

    # ── 不支持 ──
    supported = list(OPENAI_COMPATIBLE_PROVIDERS.keys()) + ["claude", "gemini"]
    raise ValueError(f"不支持的 provider: {provider}。支持: {supported}")
