"""工具函数"""
import os
import sys
from pathlib import Path


def get_project_root() -> Path:
    """获取项目根目录，兼容 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        return Path(os.path.dirname(sys.executable))
    return Path(__file__).parent.parent.parent


def get_data_dir() -> Path:
    """获取数据目录"""
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable)) / "data"
    return get_project_root() / "data"


def get_output_dir() -> Path:
    """获取输出目录"""
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable)) / "output"
    return get_project_root() / "output"
