"""PaddleOCR 手写中文识别封装

基于 PaddleOCR 2.8.x 稳定版 API。
首次运行会自动下载模型文件（约 50-100MB）。
"""

import os
import logging
from pathlib import Path
from PIL import Image

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False
    np = None  # type: ignore

logger = logging.getLogger(__name__)


class HandwritingRecognizer:
    """PaddleOCR 手写识别封装 (v2.8.x API)

    使用 ch_PP-OCRv4 模型，支持手写中文识别。
    """

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self._ocr = None
        self._last_results = []

    @property
    def ocr(self):
        """延迟加载 PaddleOCR"""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                import sys as _sys

                # 模型路径优先级:
                # 1. 环境变量 PADDLEOCR_MODELS
                # 2. PyInstaller 打包后 _internal/whl/
                # 3. C:\paddleocr_models\whl (开发者本地)
                # 4. 不指定 → PaddleOCR 自动下载到 ~/.paddleocr
                def _find_models():
                    env_path = os.environ.get("PADDLEOCR_MODELS", "")
                    if env_path:
                        return env_path

                    # PyInstaller one-file: models extracted to sys._MEIPASS
                    if getattr(_sys, 'frozen', False):
                        meipass = getattr(_sys, '_MEIPASS', '')
                        if meipass:
                            candidate = os.path.join(meipass, "whl")
                            if os.path.isdir(candidate):
                                return candidate
                        # Fallback: relative to exe
                        base = os.path.dirname(_sys.executable)
                        candidate = os.path.join(base, "whl")
                        if os.path.isdir(candidate):
                            return candidate

                    dev_path = r"C:\paddleocr_models\whl"
                    if os.path.isdir(dev_path):
                        return dev_path

                    return ""  # Let PaddleOCR auto-download

                MODEL_BASE = _find_models()
                if MODEL_BASE and os.path.isdir(MODEL_BASE):
                    det_dir = os.path.join(MODEL_BASE, "det", "ch",
                                           "ch_PP-OCRv4_det_infer")
                    rec_dir = os.path.join(MODEL_BASE, "rec", "ch",
                                           "ch_PP-OCRv4_rec_infer")
                    cls_dir = os.path.join(MODEL_BASE, "cls",
                                           "ch_ppocr_mobile_v2.0_cls_infer")
                    logger.info(f"PaddleOCR models: {MODEL_BASE}")
                    self._ocr = PaddleOCR(
                        lang='ch',
                        det_model_dir=det_dir,
                        rec_model_dir=rec_dir,
                        cls_model_dir=cls_dir,
                        use_angle_cls=True,
                        det_db_thresh=0.3,
                        det_db_box_thresh=0.2,
                        rec_batch_num=6,
                        use_gpu=self.use_gpu,
                        show_log=False,
                    )
                else:
                    logger.info("PaddleOCR 模型未预装，将自动下载...")
                    self._ocr = PaddleOCR(
                        lang='ch',
                        use_angle_cls=True,
                        det_db_thresh=0.3,
                        det_db_box_thresh=0.2,
                        rec_batch_num=6,
                        use_gpu=self.use_gpu,
                        show_log=False,
                    )
                logger.info("PaddleOCR v2.8 初始化成功 (PP-OCRv4)")
            except ImportError:
                raise ImportError(
                    "PaddleOCR 未安装。请运行:\n"
                    "  pip install paddlepaddle==2.6.2 paddleocr==2.8.1"
                )
        return self._ocr

    def recognize(self, image: "str | Path | Image.Image | np.ndarray"
                  ) -> list[dict]:
        """识别图片中的手写中文

        Args:
            image: 图片路径 / PIL Image / numpy array

        Returns:
            [{"text": "识别文字", "confidence": 0.95, "bbox": [...], "line_number": 1}, ...]
        """
        # PaddleOCR 2.8 → .ocr() 接受 numpy array、文件路径、或 bytes
        if isinstance(image, (str, Path)):
            # 直接传路径，PaddleOCR 自己读（最快）
            raw_results = self.ocr.ocr(str(image))
        elif isinstance(image, Image.Image):
            # PIL Image → numpy array
            img_array = np.array(image.convert("RGB")) if _HAS_NUMPY else image
            raw_results = self.ocr.ocr(img_array)
        else:
            # 已经是 numpy array
            raw_results = self.ocr.ocr(image)

        # 解析结果
        results = []
        line_num = 0

        if raw_results and raw_results[0]:
            for item in raw_results[0]:
                bbox = item[0]
                text_info = item[1]
                text = text_info[0]
                confidence = text_info[1]

                line_num += 1
                results.append({
                    "text": text.strip(),
                    "confidence": round(confidence, 4),
                    "bbox": bbox,
                    "line_number": line_num,
                })

        return results

    def recognize_to_text(self, image, line_separator: str = "\n") -> str:
        """识别后直接返回合并文本"""
        results = self.recognize(image)
        return line_separator.join([r["text"] for r in results])

    @property
    def overall_confidence(self) -> float:
        """最近一次识别的整体置信度"""
        if not self._last_results:
            return 0.0
        confs = [r["confidence"] for r in self._last_results]
        return sum(confs) / len(confs) if confs else 0.0

    def recognize_with_confidence(self, image
                                  ) -> tuple[str, float, list[dict]]:
        """识别并返回 (文本, 置信度, 详细结果)"""
        results = self.recognize(image)
        self._last_results = results

        if not results:
            return "", 0.0, []

        text = "\n".join([r["text"] for r in results])
        confidence = self.overall_confidence

        return text, round(confidence, 4), results


# 全局单例
_recognizer: HandwritingRecognizer | None = None


def get_recognizer(use_gpu: bool = False) -> HandwritingRecognizer:
    """获取全局 HandwritingRecognizer 单例"""
    global _recognizer
    if _recognizer is None:
        _recognizer = HandwritingRecognizer(use_gpu=use_gpu)
    return _recognizer
