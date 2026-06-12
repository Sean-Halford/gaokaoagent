"""Pydantic 数据模型"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Strength(BaseModel):
    """优点"""
    point: str = ""
    detail: str = ""


class Weakness(BaseModel):
    """缺点"""
    point: str = ""
    severity: str = "medium"
    detail: str = ""


class Suggestion(BaseModel):
    """改进建议"""
    target: str = ""
    action: str = ""
    practice: str = ""


class OCRResult(BaseModel):
    """OCR 后处理结果"""
    text: str = ""
    confidence: float = 0.0
    low_confidence_zones: list[dict] = Field(default_factory=list)
    structure: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    """一次评估的完整结果"""
    confirmed_text: str = ""
    ocr_confidence: float = 1.0
    strengths: list = Field(default_factory=list)
    weaknesses: list = Field(default_factory=list)
    suggestions: list = Field(default_factory=list)
    mistake_tags: list[str] = Field(default_factory=list)
    knowledge_gaps: list[str] = Field(default_factory=list)
    overall_assessment: str = ""
    reference_ids: list[str] = Field(default_factory=list)
    model_used: str = ""
    tokens_used: int = 0


class SubmissionRecord(BaseModel):
    """数据库中的一条提交记录"""
    id: Optional[int] = None
    image_path: str = ""
    image_hash: str = ""
    timestamp: Optional[datetime] = None
    question_type: str = ""
    question_text: str = ""
    student_text: str = ""
    strengths: str = "[]"
    weaknesses: str = "[]"
    suggestions: str = "[]"
    mistake_tags: str = "[]"
    knowledge_gaps: str = "[]"
    full_report_md: str = ""
    reference_ids: str = "[]"
    model_used: str = ""
    tokens_used: int = 0
    is_mistake: bool = True
    is_reviewed: bool = False
    ocr_confidence: float = 0.0


class MistakeStats(BaseModel):
    """错题统计"""
    total_submissions: int = 0
    total_mistakes: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_tag: dict[str, int] = Field(default_factory=dict)
    top_knowledge_gaps: list = Field(default_factory=list)
