"""高考语文刷题助手 — 启动入口"""
import sys, os, logging

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else os.path.dirname(sys.executable)
os.chdir(BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

print("=" * 55)
print("  GaokaoAgent - Beijing Exam")
print("  Server starting, please wait...")
print("=" * 55)

from src.ui.app import create_app
app, css = create_app()
app.launch(
    server_port=7860,
    inbrowser=True,
    css=css,
    allowed_paths=[os.getcwd()],
)
