"""图片预处理 — 优化 PaddleOCR 手写识别效果

支持两种模式：
- 完整模式（opencv 可用）：纠偏/去噪/CLAHE/USM锐化
- 轻量模式（仅 Pillow）：缩放 + 对比度增强
"""

import logging
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
from src.utils.image_utils import load_image, resize_image

logger = logging.getLogger(__name__)

# 尝试导入 opencv
try:
    import cv2
    import numpy as np
    _HAS_OPENCV = True
except ImportError:
    _HAS_OPENCV = False
    logger.info("opencv 未安装，使用 Pillow 轻量预处理模式")


class ImagePreprocessor:
    """图片预处理流水线，专为手写中文优化"""

    def __init__(self, max_long_edge: int = 2048,
                 enhance_contrast: bool = True,
                 denoise: bool = True,
                 sharpen: bool = True,
                 deskew: bool = True):
        self.max_long_edge = max_long_edge
        self.enhance_contrast = enhance_contrast
        self.denoise = denoise
        self.sharpen = sharpen
        self.deskew = deskew
        self.has_opencv = _HAS_OPENCV

    def process(self, image_path: str | Path) -> Image.Image:
        """完整的预处理流水线

        Returns:
            处理后的 PIL Image，可直接送入 PaddleOCR
        """
        # 1. 加载并等比缩放
        img = load_image(image_path)
        img = resize_image(img, self.max_long_edge)

        if self.has_opencv:
            return self._process_opencv(img)
        else:
            return self._process_pillow(img)

    def _process_opencv(self, img: Image.Image) -> Image.Image:
        """使用 OpenCV 的完整预处理"""
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

        if self.deskew:
            gray = self._deskew(gray)
        if self.denoise:
            gray = cv2.medianBlur(gray, 3)
        if self.enhance_contrast:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        if self.sharpen:
            blurred = cv2.GaussianBlur(gray, (0, 0), 3.0)
            gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)

        return Image.fromarray(cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB))

    def _process_pillow(self, img: Image.Image) -> Image.Image:
        """仅使用 Pillow 的轻量预处理"""
        # 灰度化
        gray = img.convert("L")

        # 去噪（轻度中值滤波）
        if self.denoise:
            gray = gray.filter(ImageFilter.MedianFilter(size=3))

        # 对比度增强
        if self.enhance_contrast:
            enhancer = ImageEnhance.Contrast(gray)
            gray = enhancer.enhance(1.5)

        # 锐化
        if self.sharpen:
            gray = gray.filter(ImageFilter.SHARPEN)

        return gray.convert("RGB")

    def _deskew(self, gray: "np.ndarray") -> "np.ndarray":
        """检测并纠正文字倾斜（仅 OpenCV 模式）"""
        _, binary = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) < 100:
            return gray

        rect = cv2.minAreaRect(coords.astype(np.float32))
        angle = rect[-1]

        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle

        if abs(angle) < 0.5 or abs(angle) > 30:
            return gray

        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(gray, M, (w, h),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REPLICATE)
        return rotated


# 快速调用
def preprocess_image(image_path: str | Path,
                     max_long_edge: int = 2048) -> Image.Image:
    """快速预处理一张图片"""
    preprocessor = ImagePreprocessor(max_long_edge=max_long_edge)
    return preprocessor.process(image_path)
