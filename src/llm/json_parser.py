"""JSON 解析器 — 对 LLM 输出的 JSON 进行鲁棒解析和修复"""

import json
import re
import logging

logger = logging.getLogger(__name__)


class JsonParser:
    """鲁棒的 JSON 解析器

    处理 LLM 的常见输出问题：
    1. markdown 代码块包裹 (```json ... ```)
    2. 输出中夹杂解释文字
    3. 末尾多余逗号
    4. 不完整的 JSON
    5. 转义问题
    """

    @staticmethod
    def extract_json_block(text: str) -> str:
        """从文本中提取 JSON 块"""
        if not text:
            return ""

        # 尝试匹配 ```json ... ``` 或 ``` ... ```
        md_match = re.search(
            r'```(?:json)?\s*\n?(.*?)\n?```',
            text, re.DOTALL
        )
        if md_match:
            return md_match.group(1).strip()

        # 尝试匹配 { 开头 } 结尾的最大块
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]

        return text.strip()

    @staticmethod
    def fix_trailing_commas(json_str: str) -> str:
        """修复 JSON 中末尾多余的逗号"""
        # 移除对象/数组末尾逗号
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        return json_str

    @staticmethod
    def fix_unquoted_keys(json_str: str) -> str:
        """尝试修复未加引号的 key（简单情况）"""
        # 大部分 LLM 都能正确处理，这里做兜底
        return json_str

    @staticmethod
    def fix_incomplete_json(json_str: str) -> str:
        """修复不完整的 JSON — 尝试补全闭合

        检测到未闭合的括号/大括号时，尝试补全。
        只做简单的末尾补全。
        """
        if not json_str:
            return "{}"

        # 计算未闭合的括号
        open_count = json_str.count('{') - json_str.count('}')
        close_count = json_str.count('[') - json_str.count(']')

        if open_count > 0:
            json_str += '}' * open_count
        if close_count > 0:
            json_str += ']' * close_count

        return json_str

    @staticmethod
    def parse(text: str, target_schema: dict | None = None) -> dict:
        """解析 LLM 输出为 JSON 对象

        Args:
            text: LLM 原始输出文本
            target_schema: 目标 JSON Schema (用于错误时构造默认值)

        Returns:
            解析后的 dict

        Raises:
            ValueError: 解析完全失败时
        """
        if not text:
            raise ValueError("LLM 返回空响应")

        # 提取 JSON 块
        json_str = JsonParser.extract_json_block(text)

        # 尝试直接解析
        errors = []
        for parser_fn, name in [
            (lambda s: json.loads(s), "直接解析"),
            (lambda s: json.loads(JsonParser.fix_trailing_commas(s)), "去尾逗号"),
            (lambda s: json.loads(JsonParser.fix_incomplete_json(
                JsonParser.fix_trailing_commas(s))), "补全后解析"),
        ]:
            try:
                return parser_fn(json_str)
            except json.JSONDecodeError as e:
                errors.append(f"{name}: {e}")

        # 全部失败 — 尝试从原始文本正则提取关键字段
        logger.warning(f"JSON 解析全部失败，尝试正则提取: {errors}")
        extracted = JsonParser._regex_extract(text)

        if extracted:
            return extracted

        raise ValueError(
            f"无法解析 LLM 输出的 JSON。\n"
            f"错误历史: {'; '.join(errors)}\n"
            f"原始输出前500字符: {text[:500]}"
        )

    @staticmethod
    def _regex_extract(text: str) -> dict:
        """正则兜底提取关键字段"""
        result = {}

        # 提取 score
        score_match = re.search(r'"score"\s*:\s*(\d+)', text)
        if score_match:
            result["score"] = int(score_match.group(1))

        # 提取 max_score
        max_match = re.search(r'"max_score"\s*:\s*(\d+)', text)
        if max_match:
            result["max_score"] = int(max_match.group(1))

        # 提取 overall_assessment
        assess_match = re.search(
            r'"overall_assessment"\s*:\s*"([^"]+)"', text
        )
        if assess_match:
            result["overall_assessment"] = assess_match.group(1)

        # 提取 confirmed_text
        text_match = re.search(
            r'"confirmed_text"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL
        )
        if text_match:
            result["confirmed_text"] = text_match.group(1)

        if result:
            # 补充默认字段
            for field in ["strengths", "weaknesses", "suggestions",
                          "mistake_tags", "knowledge_gaps"]:
                if field not in result:
                    result[field] = []
            return result

        return {}


def safe_parse_json(text: str, default: dict | None = None) -> dict:
    """安全解析 JSON，解析失败返回默认值"""
    try:
        return JsonParser.parse(text)
    except ValueError as e:
        logger.error(str(e))
        return default or {
            "error": "JSON解析失败",
            "raw_text": text[:500],
            "score": 0,
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "mistake_tags": [],
            "overall_assessment": "评估失败，请重试"
        }
