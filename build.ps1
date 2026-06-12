<#
.SYNOPSIS
  高考语文刷题助手 — 打包脚本
  生成 Windows 可分发文件夹 dist/GaokaoAgent/
#>

$ErrorActionPreference = "Stop"
$BASE = Resolve-Path "."
$DIST = "$BASE\dist\GaokaoAgent"

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  Build GaokaoAgent Distribution" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Step 1: Clean
Write-Host "`n[1/5] Cleaning..." -ForegroundColor Yellow
if (Test-Path $DIST) { Remove-Item -Recurse -Force $DIST }
New-Item -ItemType Directory -Force -Path $DIST | Out-Null

# Step 2: Copy Python
Write-Host "[2/5] Copying Python 3.11..." -ForegroundColor Yellow
$PY_SRC = "C:\Python311"
if (-not (Test-Path "$PY_SRC\python.exe")) {
    Write-Host "ERROR: C:\Python311 not found" -ForegroundColor Red
    exit 1
}
Copy-Item -Path "$PY_SRC\*" -Destination "$DIST\python\" -Recurse -Force
Write-Host "  Python copied" -ForegroundColor Green

# Step 3: Copy source code
Write-Host "[3/5] Copying source code..." -ForegroundColor Yellow
Copy-Item -Path "$BASE\src" -Destination "$DIST\src\" -Recurse -Force
Copy-Item -Path "$BASE\config" -Destination "$DIST\config\" -Recurse -Force
Copy-Item -Path "$BASE\.env.example" -Destination "$DIST\.env.example" -Force
Write-Host "  Source code copied" -ForegroundColor Green

# Step 4: Copy PaddleOCR models
Write-Host "[4/5] Copying PaddleOCR models..." -ForegroundColor Yellow
$PADDLE_SRC = "C:\paddleocr_models\whl"
if (Test-Path $PADDLE_SRC) {
    Copy-Item -Path $PADDLE_SRC -Destination "$DIST\whl\" -Recurse -Force
    Write-Host "  PaddleOCR models copied" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Models not found at $PADDLE_SRC" -ForegroundColor Yellow
    Write-Host "  PaddleOCR will download on first run" -ForegroundColor Yellow
}

# Step 5: Create directories and launcher
Write-Host "[5/5] Creating directories and launcher..." -ForegroundColor Yellow

# Data + output dirs
@(
    "data\db", "data\raw\gaokao", "data\raw\mock",
    "output\reports", "output\mistake_books", "output\exports"
) | ForEach-Object { New-Item -ItemType Directory -Force -Path "$DIST\$_" | Out-Null }

# Launcher Python script
@'
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.getcwd(), "src"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

try:
    from dotenv import load_dotenv; load_dotenv(".env")
except Exception: pass

print("=" * 50)
print("  GaokaoAgent - Gaokao Chinese Exam")
print("  Beijing Exam · AI Grading · OCR")
print("=" * 50)
print()
print("  Browser: http://127.0.0.1:7860/")
print("  Close window to exit")
print()

from src.ui.app import create_app
app = create_app()
app.launch(server_port=7860, inbrowser=True)
'@ | Out-File -FilePath "$DIST\run.py" -Encoding utf8 -NoNewline

# Start batch
@'
@echo off
title GaokaoAgent
cd /d "%~dp0"
echo.
echo ==========================================
echo   GaokaoAgent - Beijing Exam
echo ==========================================
echo.
echo   Starting... http://127.0.0.1:7860/
echo   Close this window to exit
echo ==========================================
echo.
python\python.exe run.py
pause
'@ | Out-File -FilePath "$DIST\start.bat" -Encoding ascii

# README
@'
# GaokaoAgent - Gaokao Chinese Exam AI Assistant

## Quick Start
1. Unzip the folder
2. Double-click `start.bat`
3. Browser opens at http://127.0.0.1:7860/
4. Paste your DeepSeek API Key in the UI
5. Upload handwritten answer images and start grading

## API Keys
- **DeepSeek**: https://platform.deepseek.com/api_keys
- **Doubao (Volcengine)**: https://console.volcengine.com/ark
- **Qwen (Alibaba)**: https://dashscope.console.aliyun.com/apiKey
- **GLM (Zhipu)**: https://open.bigmodel.cn/usercenter/apikeys

## Supported Question Types
- Big Essay (Da Zuowen)
- Modern Reading
- Classical Chinese Reading
- Poetry Appreciation
- Micro Writing

## Output
- PDF reports: `output/exports/`
- Markdown reports: `output/reports/`
- Mistake database: `data/db/submissions.db`

## System Requirements
- Windows 10/11 64-bit
- No Python installation needed
- ~2GB disk space
- Internet connection (for LLM API + first PaddleOCR model download)
'@ | Out-File -FilePath "$DIST\README.md" -Encoding utf8

# Size
$size = "{0:N0} MB" -f ((Get-ChildItem -Path $DIST -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB)

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Build Complete!" -ForegroundColor Green
Write-Host "  Location: $DIST" -ForegroundColor Green
Write-Host "  Size: $size" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  To distribute: Zip the folder and share" -ForegroundColor White
Write-Host "  User runs:     Extract -> double-click start.bat" -ForegroundColor White
