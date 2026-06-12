@echo off
title Gaokao Agent

:: Try C:\Python311 first (fastest, no encoding issues)
set "PY=C:\Python311\python.exe"
if exist "%PY%" goto :found

:: Fallbacks
set "PY=%LOCALAPPDATA%\Python311\python.exe"
if exist "%PY%" goto :found
set "PY=C:\Python312\python.exe"
if exist "%PY%" goto :found

echo [ERROR] Python 3.11 not found at C:\Python311
echo Install from: https://www.python.org/downloads/
pause
exit /b 1

:found
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONPATH=%~dp0

echo ========================================
echo    Gaokao Agent
echo ========================================
echo Python: %PY%
echo.

if "%~1"=="" (
    echo Starting Web UI...
    echo Open: http://127.0.0.1:7860/
    echo.
    "%PY%" -X utf8 -m src.main ui
) else (
    "%PY%" -X utf8 -m src.main %*
)

pause