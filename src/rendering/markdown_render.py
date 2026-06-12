"""Markdown 报告渲染"""

import json
from datetime import datetime
from src.storage.models import EvaluationResult, SubmissionRecord


def render_single_report(
    evaluation: EvaluationResult,
    question_type: str = "big_essay",
    question_text: str = "",
    ocr_text: str = "",
    ocr_confidence: float = 1.0,
) -> str:
    """渲染单次评估报告为 Markdown"""
    type_names = {
        "big_essay": "大作文",
        "modern_reading": "现代文阅读",
        "classical_chinese": "文言文阅读",
        "poetry": "古代诗歌阅读",
        "micro_essay": "微写作",
    }
    type_name = type_names.get(question_type, question_type)

    lines = []
    lines.append(f"# 北京卷高考语文 · {type_name}评估报告")
    lines.append(f"\n> 📅 评估时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append(f"> 📝 题型: {type_name}（北京卷）")
    lines.append(f"> 🤖 评估模型: {evaluation.model_used}")
    if ocr_confidence < 1.0:
        lines.append(f"> 🔍 OCR 置信度: {ocr_confidence:.1%}")

    # 题目
    if question_text:
        lines.append(f"\n---\n## 📖 题目\n\n> {question_text}")

    # 学生作答
    lines.append(f"\n---\n## 📝 学生作答\n")
    display_text = evaluation.confirmed_text or ocr_text
    lines.append(display_text)

    # 优点
    if evaluation.strengths:
        lines.append(f"\n---\n## ✅ 优点 ({len(evaluation.strengths)}项)\n")
        for i, s in enumerate(evaluation.strengths, 1):
            if isinstance(s, dict):
                point, detail = s.get("point", ""), s.get("detail", "")
            else:
                point, detail = getattr(s, "point", ""), getattr(s, "detail", "")
            lines.append(f"**{i}. {point}**")
            if detail:
                lines.append(f"> {detail}")
            lines.append("")

    # 缺点
    if evaluation.weaknesses:
        lines.append(f"---\n## ⚠️ 需要改进 ({len(evaluation.weaknesses)}项)\n")
        severity_map = {
            "critical": "🔴 严重", "high": "🟠 重要",
            "medium": "🟡 一般", "low": "🟢 轻微",
        }
        for i, w in enumerate(evaluation.weaknesses, 1):
            if isinstance(w, dict):
                point, sev, detail = w.get("point", ""), w.get("severity", "medium"), w.get("detail", "")
            else:
                point, sev, detail = getattr(w, "point", ""), getattr(w, "severity", "medium"), getattr(w, "detail", "")
            sev_label = severity_map.get(sev, f"⚪ {sev}")
            lines.append(f"**{i}. {point}**  `{sev_label}`")
            if detail:
                lines.append(f"> {detail}")
            lines.append("")

    # 改进建议
    if evaluation.suggestions:
        lines.append(f"---\n## 💡 改进建议\n")
        for i, s in enumerate(evaluation.suggestions, 1):
            if isinstance(s, dict):
                target, action, practice = s.get("target", ""), s.get("action", ""), s.get("practice", "")
            else:
                target = getattr(s, "target", "")
                action = getattr(s, "action", "")
                practice = getattr(s, "practice", "")
            lines.append(f"### {i}. {target}")
            lines.append(f"**行动**: {action}")
            if practice:
                lines.append(f"**练习**: {practice}")
            lines.append("")

    # 标签
    if evaluation.mistake_tags:
        lines.append(f"---\n## 🏷️ 错题标签\n")
        lines.append(" · ".join([f"`{t}`" for t in evaluation.mistake_tags]))

    # 知识盲区
    if evaluation.knowledge_gaps:
        lines.append(f"\n## 📚 知识盲区\n")
        for gap in evaluation.knowledge_gaps:
            lines.append(f"- {gap}")

    # 综合评价
    if evaluation.overall_assessment:
        lines.append(f"\n---\n## 🎯 综合评价\n")
        lines.append(evaluation.overall_assessment)

    lines.append(f"\n---")
    lines.append(f"\n> 🖨️ 本报告由「高考语文刷题助手」自动生成 | 北京卷专用")
    lines.append(f"> ⚠️ AI 评估仅供参考，建议结合老师意见")

    return "\n".join(lines)


def render_mistake_book(records: list[SubmissionRecord],
                        title: str = "错题本") -> str:
    """渲染错题本汇总为 Markdown"""
    lines = []
    lines.append(f"# {title}")
    lines.append(f"\n> 📅 生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append(f"> 📊 共 {len(records)} 条错题记录\n")

    by_type = {}
    for r in records:
        by_type.setdefault(r.question_type, []).append(r)

    type_names = {
        "big_essay": "大作文",
        "modern_reading": "现代文阅读",
        "classical_chinese": "文言文阅读",
        "poetry": "古代诗歌阅读",
        "micro_essay": "微写作",
    }

    for qtype, items in sorted(by_type.items()):
        type_name = type_names.get(qtype, qtype)
        lines.append(f"\n## {type_name} ({len(items)}题)\n")

        for i, item in enumerate(items, 1):
            lines.append(f"### {i}. [{item.timestamp}]")
            if item.question_text:
                lines.append(f"\n**题目**: {item.question_text[:100]}")
            if item.student_text:
                lines.append(f"\n<details>")
                lines.append(f"<summary>📝 学生作答（点击展开）</summary>\n")
                lines.append(item.student_text[:500])
                lines.append(f"\n</details>\n")
            if item.mistake_tags:
                tags = json.loads(item.mistake_tags) if isinstance(item.mistake_tags, str) else item.mistake_tags
                if tags:
                    lines.append(f"**错题标签**: " + " · ".join([f"`{t}`" for t in tags]))
            lines.append("")

    lines.append(f"\n---\n## 📊 统计汇总\n")
    tag_count = {}
    for r in records:
        tags = json.loads(r.mistake_tags) if isinstance(r.mistake_tags, str) else r.mistake_tags
        if tags:
            for t in tags:
                tag_count[t] = tag_count.get(t, 0) + 1

    if tag_count:
        lines.append("### 高频错题标签\n")
        for tag, count in sorted(tag_count.items(), key=lambda x: x[1], reverse=True)[:10]:
            bar = "█" * min(count, 20)
            lines.append(f"- `{tag}`: {bar} ×{count}")

    lines.append(f"\n---")
    lines.append(f"\n> 🖨️ 由「高考语文刷题助手」自动生成 | 北京卷专用")
    return "\n".join(lines)
