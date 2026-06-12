"""LLM 配置加载与模型路由"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
import yaml

logger = logging.getLogger(__name__)

from src.utils import get_project_root as _get_root
PROJECT_ROOT = _get_root()


@dataclass
class ProviderConfig:
    """单个 LLM 提供商配置"""
    name: str
    base_url: str
    api_key_env: str
    models: dict[str, str]
    protocol: str = "openai"  # "anthropic" or "openai"


@dataclass
class TaskRoute:
    """任务 → 模型路由"""
    provider: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 4096


@dataclass
class LLMConfig:
    """LLM 全局配置"""
    providers: dict[str, ProviderConfig]
    routing: dict[str, TaskRoute]
    default_provider: str


def load_llm_config(config_path: str | Path | None = None) -> LLMConfig:
    """加载 LLM 配置文件

    Args:
        config_path: 配置文件路径，默认使用 config/llm.yaml

    Returns:
        LLMConfig 实例
    """
    if config_path is None:
        config_path = PROJECT_ROOT / "config" / "llm.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # 解析 providers
    providers = {}
    for key, data in raw.get("providers", {}).items():
        providers[key] = ProviderConfig(
            name=data["name"],
            base_url=data["base_url"],
            api_key_env=data["api_key_env"],
            models=data.get("models", {}),
            protocol=data.get("protocol", "openai"),
        )

    # 解析 routing
    routing = {}
    for task_name, data in raw.get("routing", {}).items():
        routing[task_name] = TaskRoute(
            provider=data["provider"],
            model=data["model"],
            temperature=data.get("temperature", 0.3),
            max_tokens=data.get("max_tokens", 4096),
        )

    return LLMConfig(
        providers=providers,
        routing=routing,
        default_provider=raw.get("default_provider", "deepseek"),
    )


def resolve_task(task_type: str, config: LLMConfig) -> TaskRoute:
    """根据任务类型解析应使用的模型

    Args:
        task_type: 任务类型 (big_essay / modern_reading / ...)
        config: LLM 配置

    Returns:
        TaskRoute 对象，指定 provider 和 model
    """
    if task_type in config.routing:
        return config.routing[task_type]

    # 回退到 default_provider
    provider_key = config.default_provider
    if provider_key not in config.providers:
        raise ValueError(f"默认提供商 '{provider_key}' 未配置")

    provider = config.providers[provider_key]
    # 使用该 provider 的第一个模型
    first_model = next(iter(provider.models.values()))

    return TaskRoute(provider=provider_key, model=first_model)


def resolve_api_key(provider_key: str, config: LLMConfig) -> str:
    """从环境变量获取 API Key"""
    if provider_key not in config.providers:
        raise ValueError(f"未知的 LLM 提供商: {provider_key}")

    env_var = config.providers[provider_key].api_key_env
    api_key = os.getenv(env_var)

    if not api_key:
        raise ValueError(
            f"未找到 {provider_key} 的 API Key。"
            f"请设置环境变量 {env_var}，"
            f"或在项目根目录创建 .env 文件。\n"
            f"参考 .env.example 文件填写。"
        )

    return api_key
