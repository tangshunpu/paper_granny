"""
LLM Provider 工厂

创建 LangChain ChatModel 实例。
支持 OpenAI / Claude / OpenRouter / Kimi / DashScope / DeepSeek / SiliconFlow / Ollama / vLLM。

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
        "default_model": "gpt-4o",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "google/gemini-2.5-flash",
    },
    "kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "env_key": "MOONSHOT_API_KEY",
        "default_model": "moonshot-v1-128k",
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env_key": "DASHSCOPE_API_KEY",
        "default_model": "qwen-plus",
    },
    "dashscope-coding": {
        "base_url": "https://coding.dashscope.aliyuncs.com/v1",
        "env_key": "DASHSCOPE_API_KEY",
        "default_model": "qwen-plus",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
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

        kwargs = {
            "model": model,
            "api_key": key,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if url:
            kwargs["base_url"] = url
        return ChatOpenAI(**kwargs)

    # ── 不支持 ──
    supported = list(OPENAI_COMPATIBLE_PROVIDERS.keys()) + ["claude"]
    raise ValueError(f"不支持的 provider: {provider}。支持: {supported}")
