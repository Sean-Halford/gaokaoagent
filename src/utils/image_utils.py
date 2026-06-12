"""图片处理工具"""

import hashlib
from pathlib import Path
from PIL import Image
import io


def load_image(image_path: str | Path) -> Image.Image:
    """加载图片，自动处理 EXIF 旋转"""
    img = Image.open(image_path)
    # 处理 EXIF 旋转
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    return img.convert("RGB")


def resize_image(img: Image.Image, max_long_edge: int = 2048) -> Image.Image:
    """等比缩放，长边不超过 max_long_edge"""
    w, h = img.size
    long_edge = max(w, h)
    if long_edge <= max_long_edge:
        return img
    ratio = max_long_edge / long_edge
    new_size = (int(w * ratio), int(h * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def image_to_base64(img: Image.Image, format: str = "JPEG", quality: int = 85) -> str:
    """将 PIL Image 转为 Base64 字符串"""
    buffer = io.BytesIO()
    img.save(buffer, format=format, quality=quality)
    import base64
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def image_hash(image_path: str | Path) -> str:
    """计算图片 SHA256，用于去重"""
    with open(image_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_image_info(image_path: str | Path) -> dict:
    """获取图片基本信息"""
    img = Image.open(image_path)
    return {
        "width": img.width,
        "height": img.height,
        "format": img.format,
        "mode": img.mode,
        "size_kb": Path(image_path).stat().st_size / 1024,
    }
