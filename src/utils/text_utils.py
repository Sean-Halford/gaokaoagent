"""中文文本处理工具"""

import re


def normalize_punctuation(text: str) -> str:
    """统一标点符号"""
    # 中文引号
    text = text.replace(""", "\"").replace(""", "\"")
    text = text.replace("'", "'").replace("'", "'")
    # 中文标点转半角（按需）
    return text


def clean_text(text: str) -> str:
    """清理文本：去除多余空白、统一换行"""
    # 去除行首行尾空白
    lines = [line.strip() for line in text.splitlines()]
    # 去除连续空行
    cleaned = []
    for line in lines:
        if line or (cleaned and cleaned[-1]):
            cleaned.append(line)
    return "\n".join(cleaned)


def extract_question_segments(text: str) -> list[str]:
    """从题干中提取关键句段，用于 RAG 查询扩展"""
    # 按句号、问号分句
    sentences = re.split(r'[。？！\n]', text)
    # 过滤空串和过短的句子
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def build_search_query(question_type: str, question_text: str,
                       student_text: str = "") -> str:
    """构造 RAG 检索查询"""
    type_map = {
        "big_essay": "大作文 议论文 记叙文 写作",
        "modern_reading": "现代文阅读 多文本 文学类文本 阅读理解",
        "classical_chinese": "文言文阅读 实词 虚词 翻译",
        "poetry": "古代诗歌 诗词鉴赏 意象 手法",
        "micro_essay": "微写作 实用文 议论 抒情",
    }
    parts = [type_map.get(question_type, question_type)]
    if question_text:
        parts.append(question_text[:500])
    if student_text:
        parts.append(student_text[:300])
    return " ".join(parts)


def estimate_chinese_char_count(text: str) -> int:
    """估算中文字符数（排除空白和标点）"""
    return len(re.findall(r'[一-鿿]', text))


def truncate_text(text: str, max_chars: int = 3000) -> str:
    """按中文字符数截断"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n... (原文过长，已截断，共{len(text)}字符)"
