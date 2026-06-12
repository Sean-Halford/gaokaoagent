"""OCR 后处理：纠错、格式化、置信度标记"""

import re
import logging

logger = logging.getLogger(__name__)


class OCRPostProcessor:
    """OCR 文本后处理"""

    # 常见 OCR 形状混淆字映射（手写体 → 常见误识）
    COMMON_CONFUSIONS = {
        # 高频形近字
        "己": ["已", "巳"],
        "已": ["己", "巳"],
        "曰": ["日"],
        "日": ["曰", "目"],
        "未": ["末"],
        "末": ["未"],
        "人": ["入", "八"],
        "入": ["人", "八"],
        "千": ["干", "于"],
        "干": ["千", "于"],
        "土": ["士"],
        "士": ["土"],
        "侯": ["候"],
        "候": ["侯"],
        "梁": ["粱"],
        "粱": ["梁"],
        "哀": ["衰", "衷"],
        "衰": ["哀", "衷"],
        # 高考高频出错字
        "赋": ["斌"],
        "滥": ["监"],
        "藉": ["籍"],
        "籍": ["藉"],
        "即": ["既"],
        "既": ["即"],
    }

    @staticmethod
    def mark_low_confidence(text: str, confidence: float,
                            results: list[dict], threshold: float = 0.5
                            ) -> str:
        """低置信度区域标注 [?]"""
        if confidence >= 0.8:
            return text

        # 对低置信度的行加标记
        lines = text.split("\n")
        for i, r in enumerate(results):
            if i < len(lines) and r["confidence"] < threshold:
                lines[i] = f"{lines[i]} [?]"

        return "\n".join(lines)

    @staticmethod
    def merge_lines(results: list[dict],
                    max_gap_ratio: float = 1.5) -> str:
        """基于行间距合并为段落

        将垂直间距小于平均行高 1.5 倍的连续行合并为一段。
        保留明显的段落间距。
        """
        if not results:
            return ""

        if len(results) == 1:
            return results[0]["text"]

        # 计算平均行高和行间距
        heights = []
        gaps = []
        for i, r in enumerate(results):
            bbox = r["bbox"]
            # 行高 = y 方向的高度
            h = abs(bbox[2][1] - bbox[0][1])  # 左下y - 左上y
            heights.append(h)

            if i > 0:
                prev_bottom = results[i-1]["bbox"][2][1]  # 上一行底部
                curr_top = bbox[0][1]                       # 当前行顶部
                gaps.append(curr_top - prev_bottom)

        avg_height = sum(heights) / len(heights)
        avg_gap = sum(gaps) / len(gaps) if gaps else avg_height

        # 合并
        paragraphs = []
        current_para = [results[0]["text"]]

        for i in range(1, len(results)):
            prev_bottom = results[i-1]["bbox"][2][1]
            curr_top = results[i]["bbox"][0][1]
            gap = curr_top - prev_bottom

            if gap < avg_gap * max_gap_ratio:
                # 属于同一段
                current_para.append(results[i]["text"])
            else:
                # 新段落
                paragraphs.append("".join(current_para))
                current_para = [results[i]["text"]]

        paragraphs.append("".join(current_para))
        return "\n\n".join(paragraphs)

    @staticmethod
    def detect_answer_structure(text: str) -> dict:
        """检测学生作答的结构特征

        Returns:
            {
                "has_numbered_points": bool,    # 是否有分点作答
                "numbered_pattern": str,         # 分点模式
                "paragraph_count": int,          # 段落数
                "total_chars": int,              # 总字符数
                "has_bullet_points": bool,       # 是否有序号
            }
        """
        # 检测分点模式
        patterns = {
            "①②③": r'[①②③④⑤⑥⑦⑧⑨⑩]',
            "1.2.3.": r'(?:^|\n)\s*\d+[\.\)、]\s*',
            "(1)(2)": r'(?:^|\n)\s*[（(]\d+[）)]\s*',
            "一、二、": r'(?:^|\n)\s*[一二三四五六七八九十]+[、．.]',
        }

        structure = {
            "has_numbered_points": False,
            "numbered_pattern": None,
            "paragraph_count": len(text.split("\n\n")),
            "total_chars": len(text),
            "has_bullet_points": False,
        }

        for pattern_name, regex in patterns.items():
            matches = re.findall(regex, text)
            if len(matches) >= 2:
                structure["has_numbered_points"] = True
                structure["has_bullet_points"] = True
                structure["numbered_pattern"] = pattern_name
                break

        return structure

    @staticmethod
    def postprocess(results: list[dict], confidence: float) -> dict:
        """完整的后处理流水线

        Returns:
            {
                "text": "最终文本",
                "confidence": 0.85,
                "low_confidence_zones": [...],
                "structure": {...},
                "warnings": [...]
            }
        """
        if not results:
            return {
                "text": "",
                "confidence": 0.0,
                "low_confidence_zones": [],
                "structure": {},
                "warnings": ["OCR 未识别到任何文字"]
            }

        # 合并段落
        text = OCRPostProcessor.merge_lines(results)

        # 标记低置信度区域
        text = OCRPostProcessor.mark_low_confidence(
            text, confidence, results
        )

        # 分析结构
        structure = OCRPostProcessor.detect_answer_structure(text)

        # 生成警告
        warnings = []
        if confidence < 0.6:
            warnings.append(
                f"整体识别置信度较低 ({confidence:.0%})，建议重新拍照或手动校对"
            )
        if not structure["has_numbered_points"]:
            warnings.append("未检测到分点作答格式，北京卷建议分点作答更清晰")

        # 收集低置信度区域
        low_conf_zones = [
            {"text": r["text"], "confidence": r["confidence"]}
            for r in results if r["confidence"] < 0.5
        ]

        return {
            "text": text,
            "confidence": confidence,
            "low_confidence_zones": low_conf_zones,
            "structure": structure,
            "warnings": warnings,
        }
