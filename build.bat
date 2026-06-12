@echo off
chcp 65001 >nul
title Build GaokaoAgent

set "PY=C:\Python311\python.exe"
if not exist "%PY%" set "PY=%LOCALAPPDATA%\Python311\python.exe"
if not exist "%PY%" (echo Python 3.11 not found & pause & exit /b 1)

echo ==========================================
echo   Build GaokaoAgent - 高考语文刷题助手
echo ==========================================
echo.

echo [1/3] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo Done.

echo [2/3] Building with PyInstaller...
"%PY%" -X utf8 -m PyInstaller build.spec --clean --noconfirm
if %ERRORLEVEL% neq 0 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo [3/3] Preparing distribution package...
set DIST=dist\GaokaoAgent

:: Copy runtime files
copy /Y run.bat "%DIST%\start.bat" >nul
copy /Y .env.example "%DIST%\.env.example" >nul

:: Create empty data directories
mkdir "%DIST%\data\db" 2>nul
mkdir "%DIST%\data\raw\gaokao" 2>nul
mkdir "%DIST%\data\raw\mock" 2>nul
mkdir "%DIST%\output\reports" 2>nul
mkdir "%DIST%\output\mistake_books" 2>nul
mkdir "%DIST%\output\exports" 2>nul

:: Create startup batch
(
echo @echo off
echo title GaokaoAgent
echo cd /d "%%~dp0"
echo echo.
echo echo ==========================================
echo echo   高考语文刷题助手 - 北京卷专用
echo echo ==========================================
echo echo.
echo echo   启动中...浏览器将自动打开
echo echo   http://127.0.0.1:7860/
echo echo.
echo echo   ^^关闭此窗口即可退出
echo echo ==========================================
echo echo.
echo GaokaoAgent.exe
echo pause
) > "%DIST%\GaokaoAgent.bat"

:: Create readme
(
echo # 高考语文刷题助手 — 安装使用说明
echo.
echo ## 系统要求
echo - Windows 10/11 64位
echo - 无需安装 Python
echo - 首次运行需要联网（下载 OCR 模型，约 100MB）
echo.
echo ## 安装步骤
echo 1. 双击 `GaokaoAgent.bat` 启动
echo 2. 浏览器自动打开 http://127.0.0.1:7860/
echo 3. 在界面中粘贴 DeepSeek API Key
echo 4. 上传手写答案图片，开始评估
echo.
echo ## 配置 API Key
echo - **方式一（推荐）**: 在 Web 界面中直接粘贴 Key
echo - **方式二**: 复制 `.env.example` 为 `.env`，填入 API Key
echo.
echo ## 退出
echo 关闭命令行窗口即可。
echo.
echo ## 输出文件
echo - 评估报告 PDF: `output/exports/`
echo - Markdown 报告: `output/reports/`
echo - 错题数据库: `data/db/submissions.db`
echo.
echo ## 常见问题
echo **Q: 启动后 OCR 识别失败？**
echo A: 首次运行需要下载 OCR 模型，请确保网络畅通。
echo.
echo **Q: 评估返回错误？**
echo A: 请检查 API Key 是否正确，网络是否能访问 api.deepseek.com。
echo.
echo **Q: PDF 导出乱码？**
echo A: 请确保系统安装了中文字体（如微软雅黑、宋体）。
) > "%DIST%\README.md"

echo.
echo ==========================================
echo   Build Complete!
echo ==========================================
echo.
echo   Location: %DIST%
echo   Size: ~800MB (包含 Python + PaddleOCR)
echo.
echo   发送给用户: 将整个 GaokaoAgent 文件夹压缩为 .zip
echo   用户使用: 解压 → 双击 GaokaoAgent.bat
echo.
pause
