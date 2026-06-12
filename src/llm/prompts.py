"""System Prompt 模板与组装"""

import json
import yaml
from pathlib import Path

from src.utils import get_project_root as _get_root
PROJECT_ROOT = _get_root()


def load_beijing_rubrics() -> dict:
    """加载北京卷评分标准"""
    rubrics_path = PROJECT_ROOT / "config" / "beijing_gaokao.yaml"
    with open(rubrics_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_rubrics_for_type(question_type: str) -> str:
    """获取某题型的评分标准文本"""
    data = load_beijing_rubrics()
    types = data.get("question_types", {})

    if question_type not in types:
        return f"题型 '{question_type}' 的评分标准暂无，请按北京卷通用标准评估。"

    qt = types[question_type]

    parts = [f"## {qt['name']}（满分{qt['max_score']}分）"]
    parts.append(f"\n{qt.get('description', '')}")

    if "grading_dimensions" in qt:
        parts.append("\n### 评分维度")
        for dim in qt["grading_dimensions"]:
            parts.append(
                f"- **{dim['name']}**（满分{dim['max_score']}分，权重{dim['weight']:.0%}）："
                f"{dim['description']}"
            )
            if "scoring_levels" in dim:
                parts.append("  等级标准：")
                for level in dim["scoring_levels"]:
                    range_str = f"{level['range'][0]}-{level['range'][1]}"
                    parts.append(
                        f"  · {level['level']}（{range_str}分）：{level['criteria']}"
                    )

    if "common_mistakes" in qt:
        parts.append("\n### 常见失分模式")
        for m in qt["common_mistakes"]:
            tag = m.get('tag', '')
            severity = m.get('severity', 'medium')
            desc = m.get('description', '')
            fix_hint = m.get('fix', '请参考评分标准中的相应等级要求')
            parts.append(
                f"- **{tag}** (严重度: {severity})：{desc}\n"
                f"  改进方向：{fix_hint}"
            )

    if "subtypes" in qt:
        for sub_key, sub in qt["subtypes"].items():
            if isinstance(sub, dict):
                parts.append(f"\n#### {sub.get('name', sub_key)}（{sub.get('description', '')}）")
                if "grading_dimensions" in sub:
                    for dim in sub["grading_dimensions"]:
                        parts.append(
                            f"- **{dim.get('name', '')}**（{dim.get('max_score', 0)}分）：{dim.get('description', '')}"
                        )
                if "common_mistakes" in sub:
                    parts.append("  常见失分：")
                    for m in sub["common_mistakes"]:
                        tag = m.get('tag', '')
                        parts.append(f"  - {tag}：{m.get('description', '')}")

    return "\n".join(parts)


def get_beijing_knowledge() -> str:
    """获取北京卷特色考点知识"""
    data = load_beijing_rubrics()
    bk = data.get("beijing_specific_knowledge", {})

    parts = ["## 北京卷特色考点"]

    if "classics" in bk:
        parts.append("\n### 名著阅读考查要点")
        for classic in bk["classics"]:
            parts.append(f"\n#### 《{classic['name']}》")
            parts.append(f"考查范围：{classic['exam_scope']}")
            parts.append("核心知识点：")
            for kp in classic.get("key_points", []):
                parts.append(f"  - {kp}")
            if classic.get("common_question_types"):
                parts.append("常见题型：")
                for qt in classic["common_question_types"]:
                    parts.append(f"  - {qt}")

    if "culture" in bk:
        parts.append("\n### 文化常识考查")
        for c in bk["culture"]:
            parts.append(f"\n#### {c['name']}")
            parts.append(f"关联：{c.get('relevance', '')}")

    return "\n".join(parts)


def build_system_prompt(question_type: str, question_text: str,
                        ocr_confidence: float = 1.0) -> str:
    """构造评估的 System Prompt

    Args:
        question_type: 题型 (big_essay / modern_reading / ...)
        question_text: 题干文本
        ocr_confidence: OCR 识别置信度

    Returns:
        完整的 System Prompt 字符串
    """
    rubrics = get_rubrics_for_type(question_type)
    beijing_knowledge = get_beijing_knowledge()

    type_names = {
        "big_essay": "大作文",
        "modern_reading": "现代文阅读",
        "classical_chinese": "文言文阅读",
        "poetry": "古代诗歌阅读",
        "micro_essay": "微写作",
    }
    type_name = type_names.get(question_type, question_type)

    prompt = f"""你是北京市重点高中语文教师，拥有20年北京卷高考阅卷经验。
你精通北京卷语文的命题趋势、评分标准和学生常见失分模式。

{rubrics}

{beijing_knowledge}

## 评估任务

你正在评估一份**{type_name}**的学生作答。学生的手写答案已通过 OCR 识别为文本（置信度: {ocr_confidence:.0%}）。

### 题目
{question_text}

### 学生作答 (OCR识别文本)
{{ocr_text}}

### 评估要求

请严格按以下步骤完成评估，输出 JSON：

1. **文本确认**: OCR 可能有识别错误。结合语境和常识智能修正，给出最终作答文本。
2. **得分识别**: 如果 OCR 识别出的学生作答文本中包含了题目给出的总分（如"本题满分50分"），请识别并记录该总分；如果没有明确给出总分，则不需要评分。
3. **对标分析**: 你的评判依据是什么？北京卷该题型的核心得分点有哪些？
4. **优点**: 至少列出 3 个学生的优点。
5. **缺点与改进**: 每个缺点给出严重度（critical/high/medium/low）和具体可操作的改进建议。
6. **错题标签**: 标记错误类型标签。
7. **知识点漏洞**: 列出暴露的知识盲区。
8. **总体评价**: 一段话综合评价，指出备考方向。

### JSON 输出格式

严格按照以下 JSON 结构输出（不要添加其他内容）：
{{
  "confirmed_text": "确认后的学生作答文本",
  "strengths": [
    {{ "point": "优点描述", "detail": "详细说明" }}
  ],
  "weaknesses": [
    {{ "point": "缺点描述", "severity": "high", "detail": "详细说明" }}
  ],
  "suggestions": [
    {{
      "target": "改进目标",
      "action": "具体行动建议",
      "practice": "练习建议"
    }}
  ],
  "mistake_tags": ["标签1", "标签2"],
  "knowledge_gaps": ["知识点1", "知识点2"],
  "overall_assessment": "综合评价一段话"
}}

请严格遵守以下规则：
- 输出纯 JSON，不要有 markdown 代码块标记
- 如果 OCR 文本中有题目总分信息，请在 confirmed_text 中保留
- 改进建议必须具体可操作，不能是空泛的"多练习"
- 错题标签从常见失分模式中选择，也可自定义"""

    return prompt


def build_user_message(ocr_text: str, question_text: str = "",
                       extra_context: str = "") -> str:
    """构造 User Message

    Args:
        ocr_text: OCR 识别出的学生作答文本
        question_text: 题干
        extra_context: 额外的上下文（如 RAG 检索结果）

    Returns:
        用户消息字符串
    """
    parts = []
    parts.append("请评估以下学生作答：\n")

    parts.append(f"--- 学生作答文本 ---\n{ocr_text}\n--- 结束 ---")

    if question_text:
        parts.append(f"\n（题目原文：{question_text[:200]}）")

    if extra_context:
        parts.append(f"\n### 参考资料\n{extra_context}")

    parts.append("\n请按上述 JSON Schema 给出评估结果。")

    return "\n".join(parts)


def build_rag_context(retrieved_docs: list[dict]) -> str:
    """将 RAG 检索结果格式化为参考上下文"""
    if not retrieved_docs:
        return ""

    parts = ["## 历年真题参考（知识库检索）\n"]
    parts.append("以下是历年北京卷和模拟卷中与本题最相似的题目及官方答案，请在评估时参考对标：\n")

    for i, doc in enumerate(retrieved_docs, 1):
        metadata = doc.get("metadata", {})
        content = doc.get("content") or doc.get("document", "")

        title_parts = []
        if metadata.get("year"):
            title_parts.append(str(metadata["year"]))
        if metadata.get("source"):
            title_parts.append(metadata["source"])
        if metadata.get("subtype"):
            title_parts.append(f"({metadata.get('subtype', '')})")

        title = f"参考题 {i} — {' · '.join(title_parts)}"
        if doc.get("similarity"):
            title += f" [相似度: {doc['similarity']:.2f}]"

        parts.append(f"### {title}")
        truncated = content[:1500]
        if len(content) > 1500:
            truncated += f"\n\n... (共 {len(content)} 字符，已截断)"
        parts.append(truncated)
        parts.append("")

    return "\n".join(parts)


def get_json_schema_for_type(question_type: str) -> dict:
    """获取某题型的输出 JSON Schema"""
    return {
        "type": "object",
        "properties": {
            "confirmed_text": {"type": "string"},
            "strengths": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "point": {"type": "string"},
                        "detail": {"type": "string"},
                    },
                    "required": ["point"]
                }
            },
            "weaknesses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "point": {"type": "string"},
                        "severity": {"type": "string"},
                        "detail": {"type": "string"},
                    },
                    "required": ["point", "severity"]
                }
            },
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "action": {"type": "string"},
                        "practice": {"type": "string"},
                    }
                }
            },
            "mistake_tags": {"type": "array", "items": {"type": "string"}},
            "knowledge_gaps": {"type": "array", "items": {"type": "string"}},
            "overall_assessment": {"type": "string"},
        },
        "required": ["strengths", "weaknesses", "suggestions",
                     "mistake_tags", "overall_assessment"]
    }
