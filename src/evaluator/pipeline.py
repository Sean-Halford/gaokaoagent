"""评估管线 — 编排 OCR → LLM → 存储 → 渲染 全流程"""

import json
import logging
from pathlib import Path
from datetime import datetime

from src.ocr.preprocessor import ImagePreprocessor
from src.ocr.recognizer import get_recognizer
from src.ocr.postprocessor import OCRPostProcessor
from src.evaluator.grader import Grader
from src.storage.models import SubmissionRecord
from src.storage import database
from src.rendering.markdown_render import render_single_report
from src.utils.image_utils import image_hash

logger = logging.getLogger(__name__)


def _to_json_str(obj) -> str:
    """将对象序列化为 JSON 字符串（用于数据库存储）"""
    if obj is None:
        return "[]"
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        items = []
        for item in obj:
            if hasattr(item, "model_dump"):
                items.append(item.model_dump())
            elif isinstance(item, dict):
                items.append(item)
            else:
                items.append(str(item))
        return json.dumps(items, ensure_ascii=False, default=str)
    if isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False, default=str)
    return json.dumps(obj, ensure_ascii=False, default=str)


class EvaluationPipeline:
    """评估管线

    Usage:
        pipeline = EvaluationPipeline()
        result = pipeline.run(
            image_path="path/to/answer.jpg",
            question_type="big_essay",
            question_text="请以'韧性'为题写一篇议论文..."
        )
    """

    def __init__(self, use_gpu: bool = False):
        self.recognizer = get_recognizer(use_gpu=use_gpu)
        self.preprocessor = ImagePreprocessor()
        self.postprocessor = OCRPostProcessor()

    def run(self,
            image_path: str | Path,
            question_type: str = "big_essay",
            question_text: str = "",
            save_to_db: bool = True,
            output_dir: str | Path | None = None,
            api_key: str = "",
            base_url: str = "",
            model_name: str = "",
            ) -> dict:
        """运行完整的评估管线（图片模式）"""
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"图片不存在: {image_path}")

        logger.info(f"=== 开始评估管线 ===")
        logger.info(f"图片: {image_path.name}, 题型: {question_type}")

        # Step 1: 图片预处理
        logger.info("Step 1/4: 图片预处理...")
        processed_img = self.preprocessor.process(image_path)

        # Step 2: OCR 识别
        logger.info("Step 2/4: PaddleOCR 手写识别...")
        ocr_text, ocr_conf, ocr_results = \
            self.recognizer.recognize_with_confidence(processed_img)

        postprocessed = self.postprocessor.postprocess(ocr_results, ocr_conf)
        final_ocr_text = postprocessed["text"]
        ocr_warnings = postprocessed["warnings"]

        logger.info(f"OCR 置信度: {ocr_conf:.2%}, 文本长度: {len(final_ocr_text)}")
        for w in ocr_warnings:
            logger.warning(f"  {w}")

        # Step 3: LLM 评估
        logger.info("Step 3/4: LLM 评估...")
        grader = Grader(question_type=question_type,
                        api_key=api_key, base_url=base_url,
                        model_name=model_name)
        evaluation = grader.grade(
            ocr_text=final_ocr_text,
            question_text=question_text,
            ocr_confidence=ocr_conf,
        )

        result = Grader.to_evaluation_result(
            evaluation,
            model_used=grader.model_name,
            ocr_confidence=ocr_conf,
        )

        # Step 4: 渲染报告 & 存储
        logger.info("Step 4/4: 渲染报告...")
        return self._finalize(
            evaluation=evaluation, result=result,
            final_ocr_text=final_ocr_text, ocr_conf=ocr_conf,
            ocr_warnings=ocr_warnings,
            question_type=question_type, question_text=question_text,
            image_path=image_path, save_to_db=save_to_db,
            output_dir=output_dir,
        )

    def run_text_only(self,
                      ocr_text: str = "",
                      question_type: str = "big_essay",
                      question_text: str = "",
                      save_to_db: bool = True,
                      output_dir: str | Path | None = None,
                      api_key: str = "",
                      base_url: str = "",
                      model_name: str = "",
                      ) -> dict:
        """文本模式：跳过 OCR，直接用文本调用 LLM 评估"""
        logger.info(f"=== 文本模式评估: {question_type}, 文本长度: {len(ocr_text)} ===")

        grader = Grader(question_type=question_type,
                        api_key=api_key, base_url=base_url,
                        model_name=model_name)
        evaluation = grader.grade(
            ocr_text=ocr_text,
            question_text=question_text,
            ocr_confidence=1.0,
        )

        result = Grader.to_evaluation_result(
            evaluation,
            model_used=grader.model_name,
        )

        return self._finalize(
            evaluation=evaluation, result=result,
            final_ocr_text=ocr_text, ocr_conf=1.0,
            ocr_warnings=[],
            question_type=question_type, question_text=question_text,
            image_path=None, save_to_db=save_to_db,
            output_dir=output_dir,
        )

    def _finalize(self, evaluation, result, final_ocr_text, ocr_conf,
                  ocr_warnings, question_type, question_text,
                  image_path, save_to_db, output_dir) -> dict:
        """公共收尾：渲染报告、保存文件、入库"""
        report_md = render_single_report(
            evaluation=result,
            question_type=question_type,
            question_text=question_text,
            ocr_text=final_ocr_text,
            ocr_confidence=ocr_conf,
        )

        # 输出目录
        if output_dir:
            output_dir = Path(output_dir)
        else:
            from src.utils import get_output_dir
            output_dir = get_output_dir() / "reports"
            output_dir = output_dir / datetime.now().strftime("%Y-%m")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        type_names = {
            "big_essay": "大作文", "modern_reading": "现代文阅读",
            "classical_chinese": "文言文", "poetry": "诗歌鉴赏",
            "micro_essay": "微写作",
        }
        type_name = type_names.get(question_type, question_type)
        report_path = output_dir / f"{type_name}_{timestamp}.md"
        report_path.write_text(report_md, encoding="utf-8")
        logger.info(f"报告已保存: {report_path}")

        # 数据库
        submission_id = None
        if save_to_db:
            image_path_str = str(image_path) if image_path else "(text_input)"
            record = SubmissionRecord(
                image_path=image_path_str,
                image_hash=image_hash(image_path) if image_path else "",
                question_type=question_type,
                question_text=question_text,
                student_text=result.confirmed_text or final_ocr_text,
                strengths=_to_json_str(result.strengths),
                weaknesses=_to_json_str(result.weaknesses),
                suggestions=_to_json_str(result.suggestions),
                mistake_tags=_to_json_str(result.mistake_tags),
                knowledge_gaps=_to_json_str(result.knowledge_gaps),
                full_report_md=report_md,
                model_used=result.model_used,
                tokens_used=result.tokens_used,
                ocr_confidence=ocr_conf,
            )
            submission_id = database.insert_submission(record)
            logger.info(f"数据库记录ID: {submission_id}")

        return {
            "ocr_text": final_ocr_text,
            "ocr_confidence": ocr_conf,
            "ocr_warnings": ocr_warnings,
            "evaluation": evaluation,
            "result": result,
            "report_md": report_md,
            "report_path": report_path,
            "submission_id": submission_id,
        }


def quick_evaluate(image_path: str | Path,
                   question_type: str = "big_essay",
                   question_text: str = "",
                   **kwargs) -> dict:
    """快捷评估"""
    pipeline = EvaluationPipeline()
    return pipeline.run(
        image_path=image_path,
        question_type=question_type,
        question_text=question_text,
        **kwargs,
    )
