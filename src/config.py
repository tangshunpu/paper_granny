"""
配置管理模块

从 config.yaml 和环境变量加载配置。
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class LLMConfig:
    """LLM 后端配置"""
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096

    def __post_init__(self):
        # 环境变量优先级高于配置文件
        env_key_map = {
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "kimi": "MOONSHOT_API_KEY",
            "dashscope": "DASHSCOPE_API_KEY",
            "dashscope-coding": "DASHSCOPE_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "siliconflow": "SILICONFLOW_API_KEY",
        }
        if not self.api_key and self.provider in env_key_map:
            self.api_key = os.environ.get(env_key_map[self.provider], "")

        # Ollama 默认 base_url
        if self.provider == "ollama" and not self.base_url:
            self.base_url = "http://localhost:11434/v1"


@dataclass
class TemplateConfig:
    """模板配置"""
    default: str = "ModernColorful"
    directory: str = "latex_template"


@dataclass
class OutputConfig:
    """输出配置"""
    directory: str = "papers"
    naming: str = "{topic}_论文解读"


@dataclass
class CompilerConfig:
    """编译器配置"""
    engine: str = "xelatex"
    runs: int = 2
    cleanup: bool = True


@dataclass
class AppConfig:
    """应用总配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    template: TemplateConfig = field(default_factory=TemplateConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    compiler: CompilerConfig = field(default_factory=CompilerConfig)


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个字典，override 中的值覆盖 base。"""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    加载配置文件。
    
    优先级: CLI 参数 > 环境变量 > config.local.yaml > config.yaml > 默认值
    """
    config = AppConfig()

    # 寻找配置文件
    if config_path is None:
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.yaml"
    else:
        config_path = Path(config_path)

    config_path = Path(config_path)
    raw = {}

    # 加载主配置
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    # 加载用户本地覆盖配置 (config.local.yaml)
    local_config_path = config_path.parent / "config.local.yaml"
    if local_config_path.exists():
        with open(local_config_path, "r", encoding="utf-8") as f:
            local_raw = yaml.safe_load(f) or {}
        raw = _deep_merge(raw, local_raw)

    if "llm" in raw:
        config.llm = LLMConfig(**{
            k: v for k, v in raw["llm"].items()
            if k in LLMConfig.__dataclass_fields__
        })
    if "template" in raw:
        config.template = TemplateConfig(**{
            k: v for k, v in raw["template"].items()
            if k in TemplateConfig.__dataclass_fields__
        })
    if "output" in raw:
        config.output = OutputConfig(**{
            k: v for k, v in raw["output"].items()
            if k in OutputConfig.__dataclass_fields__
        })
    if "compiler" in raw:
        config.compiler = CompilerConfig(**{
            k: v for k, v in raw["compiler"].items()
            if k in CompilerConfig.__dataclass_fields__
        })

    return config
