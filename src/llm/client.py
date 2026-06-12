"""统一 LLM 客户端 — OpenAI 兼容协议

支持 DeepSeek / 豆包 / 千问 / GLM 等所有 OpenAI 兼容的模型，
通过配置文件切换，不绑定任何一家。
"""

import logging
from openai import OpenAI
from src.llm.config import (
    LLMConfig, TaskRoute, ProviderConfig,
    load_llm_config, resolve_task, resolve_api_key
)

logger = logging.getLogger(__name__)


class LLMClient:
    """统一的 LLM 调用接口

    Usage:
        config = load_llm_config()
        route = resolve_task("big_essay", config)
        api_key = resolve_api_key(route.provider, config)

        client = LLMClient(config, route, api_key)
        response = client.chat([
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
        ])
    """

    def __init__(self, config: LLMConfig, route: TaskRoute, api_key: str,
                 base_url: str | None = None, model_name: str | None = None):
        self.config = config
        self.route = route

        provider = config.providers[route.provider]
        actual_base_url = base_url or provider.base_url
        actual_model = model_name or provider.models.get(route.model, route.model)

        logger.info(
            f"LLM 客户端初始化: model={actual_model}, "
            f"base_url={actual_base_url[:40]}..."
        )

        self.client = OpenAI(api_key=api_key, base_url=actual_base_url)
        self.model_name = actual_model

    def chat(self, messages: list[dict],
             temperature: float | None = None,
             max_tokens: int | None = None,
             json_mode: bool = True) -> str:
        """发送对话请求

        Args:
            messages: OpenAI 格式的消息列表
            temperature: 温度参数，默认使用配置值
            max_tokens: 最大 token 数，默认使用配置值
            json_mode: 是否启用 JSON 输出模式

        Returns:
            LLM 响应文本
        """
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature or self.route.temperature,
            "max_tokens": max_tokens or self.route.max_tokens,
        }

        # DeepSeek 支持 response_format，但对 JSON Schema 约束有限
        # 只用 json_object 模式，Schema 描述写在 prompt 里
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content

            # 记录 token 使用
            if hasattr(response, 'usage') and response.usage:
                logger.debug(
                    f"Token 使用: prompt={response.usage.prompt_tokens}, "
                    f"completion={response.usage.completion_tokens}"
                )

            return content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    def chat_with_retry(self, messages: list[dict],
                        max_retries: int = 2,
                        **kwargs) -> str:
        """带重试的对话请求"""
        import time

        for attempt in range(max_retries + 1):
            try:
                return self.chat(messages, **kwargs)
            except Exception as e:
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning(
                        f"LLM 调用失败 (尝试 {attempt+1}/{max_retries+1}): "
                        f"{e}，{wait}秒后重试..."
                    )
                    time.sleep(wait)
                else:
                    raise


def create_client_for_task(task_type: str) -> LLMClient:
    """快捷方法：根据任务类型创建客户端

    Usage:
        client = create_client_for_task("big_essay")
        response = client.chat([...])
    """
    config = load_llm_config()
    route = resolve_task(task_type, config)
    api_key = resolve_api_key(route.provider, config)
    return LLMClient(config, route, api_key)
