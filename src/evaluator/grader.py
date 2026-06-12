"""评估逻辑 — 调用 LLM 进行评估并解析结果

支持两种协议：
- Anthropic (DeepSeek): anthropic.Anthropic SDK
- OpenAI (豆包/千问/GLM): openai.OpenAI SDK
"""

import os
import json
import logging
from src.llm.config import load_llm_config, resolve_task
from src.llm.prompts import build_system_prompt, build_user_message
from src.llm.json_parser import JsonParser
from src.storage.models import EvaluationResult

logger = logging.getLogger(__name__)


def _build_anthropic_client(api_key: str, base_url: str, model_name: str,
                            temperature: float, max_tokens: int):
    """构建 Anthropic 协议客户端

    DeepSeek Anthropic 端点使用 Bearer Token 认证 (auth_token)，
    而非 x-api-key (api_key)。
    """
    import anthropic
    client = anthropic.Anthropic(
        base_url=base_url,
        auth_token=api_key,         # → Authorization: Bearer sk-xxx
    )
    return {
        "protocol": "anthropic",
        "client": client,
        "model": model_name,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def _build_openai_client(api_key: str, base_url: str, model_name: str,
                         temperature: float, max_tokens: int):
    """构建 OpenAI 协议客户端 (豆包/千问/GLM)"""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    return {
        "protocol": "openai",
        "client": client,
        "model": model_name,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def chat_anthropic(client_info: dict, system_prompt: str,
                   user_message: str) -> str:
    """Anthropic 协议调用 (DeepSeek V4 Pro 含 reasoning blocks)"""
    c = client_info["client"]
    response = c.messages.create(
        model=client_info["model"],
        max_tokens=client_info["max_tokens"],
        temperature=client_info["temperature"],
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    # DeepSeek V4 Pro returns [ThinkingBlock, TextBlock] — pick text blocks
    text_parts = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
    if not text_parts:
        raise ValueError("Anthropic 响应中无 text 块: " +
                         str([b.type for b in response.content]))
    return "".join(text_parts)


def chat_openai(client_info: dict, system_prompt: str,
                user_message: str) -> str:
    """OpenAI 协议调用"""
    c = client_info["client"]
    response = c.chat.completions.create(
        model=client_info["model"],
        max_tokens=client_info["max_tokens"],
        temperature=client_info["temperature"],
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content


def _build_client(question_type: str, api_key: str,
                  base_url: str, model_name: str) -> dict:
    """构建 LLM 客户端（支持 Anthropic 和 OpenAI 协议）

    Returns:
        {"protocol": "anthropic"|"openai", "client": ..., "model": ..., ...}
    """
    config = load_llm_config()
    route = resolve_task(question_type, config)
    provider = config.providers[route.provider]

    key = api_key or os.getenv(provider.api_key_env, "")
    url = base_url or provider.base_url
    model = model_name or provider.models.get(route.model, "deepseek-v4-pro[1m]")
    protocol = provider.protocol

    if not key:
        raise ValueError(
            f"未提供 API Key。请在界面粘贴 Key，"
            f"或设置环境变量 {provider.api_key_env}"
        )

    logger.info(f"LLM: protocol={protocol}, model={model}")

    if protocol == "anthropic":
        return _build_anthropic_client(key, url, model,
                                       route.temperature, route.max_tokens)
    else:
        return _build_openai_client(key, url, model,
                                    route.temperature, route.max_tokens)


class Grader:
    """评估器"""

    def __init__(self, question_type: str = "big_essay",
                 api_key: str = "", base_url: str = "",
                 model_name: str = ""):
        self.client_info = _build_client(question_type, api_key,
                                         base_url, model_name)
        self.question_type = question_type
        self._model_name = self.client_info["model"]

    @property
    def model_name(self) -> str:
        return self._model_name

    def grade(self, ocr_text: str,
              question_text: str = "",
              ocr_confidence: float = 1.0,
              extra_context: str = "") -> dict:
        """执行一次评估"""
        system_prompt = build_system_prompt(
            question_type=self.question_type,
            question_text=question_text,
            ocr_confidence=ocr_confidence,
        )
        system_prompt = system_prompt.replace("{ocr_text}", ocr_text)

        user_message = build_user_message(
            ocr_text=ocr_text,
            question_text=question_text,
            extra_context=extra_context,
        )

        logger.info(f"评估: 题型={self.question_type}, 文本={len(ocr_text)}字")

        for attempt in range(3):
            try:
                if self.client_info["protocol"] == "anthropic":
                    raw = chat_anthropic(self.client_info,
                                         system_prompt, user_message)
                else:
                    raw = chat_openai(self.client_info,
                                      system_prompt, user_message)
                return self._normalize(JsonParser.parse(raw))
            except Exception as e:
                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)
                    logger.warning(f"LLM 重试 {attempt+1}: {e}")
                else:
                    raise

    def _normalize(self, raw: dict) -> dict:
        def _items(lst):
            result = []
            for s in lst:
                if isinstance(s, dict):
                    result.append({
                        "point": s.get("point", ""),
                        "detail": s.get("detail", ""),
                        "severity": s.get("severity", "medium"),
                        "target": s.get("target", ""),
                        "action": s.get("action", ""),
                        "practice": s.get("practice", ""),
                    })
            return result

        return {
            "confirmed_text": raw.get("confirmed_text", ""),
            "strengths": _items(raw.get("strengths", [])),
            "weaknesses": _items(raw.get("weaknesses", [])),
            "suggestions": _items(raw.get("suggestions", [])),
            "mistake_tags": raw.get("mistake_tags", []),
            "knowledge_gaps": raw.get("knowledge_gaps", []),
            "overall_assessment": raw.get("overall_assessment", ""),
        }

    @staticmethod
    def to_evaluation_result(data: dict, model_used: str = "",
                             tokens_used: int = 0,
                             ocr_confidence: float = 1.0
                             ) -> EvaluationResult:
        return EvaluationResult(
            confirmed_text=data.get("confirmed_text", ""),
            ocr_confidence=ocr_confidence,
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            suggestions=data.get("suggestions", []),
            mistake_tags=data.get("mistake_tags", []),
            knowledge_gaps=data.get("knowledge_gaps", []),
            overall_assessment=data.get("overall_assessment", ""),
            model_used=model_used,
            tokens_used=tokens_used,
        )
