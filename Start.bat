@echo off
chcp 65001 >nul
title COD Highlight Cutter v3.0
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║           COD HIGHLIGHT CUTTER v3.0                          ║
echo  ║           Auto-Installer ^& Launcher                         ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.9+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check Tesseract OCR
where tesseract >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Tesseract OCR not found in PATH!
    echo Please install from: https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo Press any key to continue anyway (OCR detection will be limited)...
    pause >nul
)

REM Create virtual environment if not exists
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install/Update dependencies
echo [2/4] Checking dependencies...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)

echo [3/4] Dependencies ready!
echo.

REM Check for video file
echo [4/4] Ready to process!
echo.
echo Place your COD gameplay video in this folder and drag it onto this .bat file,
echo or run manually: python main.py "your_video.mp4"
echo.

if "%~1"=="" (
    echo [INFO] No video file provided.
    echo.
    echo Usage: Drag and drop your video onto Start.bat
echo        Or: Start.bat "path\to\your\video.mp4"
    echo.
    echo Press any key to open the output folder...
    pause >nul
    if not exist "output" mkdir output
    explorer output
) else (
    echo [PROCESSING] %~1
    echo.
    python main.py "%~1" --tiktok --individual --music "assets/music/background.mp3"
    echo.
    echo [DONE] Check the output folder!
    pause
)
