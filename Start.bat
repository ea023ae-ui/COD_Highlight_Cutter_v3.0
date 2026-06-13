@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title COD Highlight Cutter v3.0
color 0A

:MENU
cls
echo.
echo  ==========================================
echo   COD HIGHLIGHT CUTTER v3.0
echo   Auto-Installer and Launcher
echo  ==========================================
echo.

REM --- CHECK PYTHON ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.9+
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

REM --- CHECK TESSERACT ---
set "TESSERACT_FOUND=0"

REM Check PATH first
where tesseract >nul 2>&1
if errorlevel 0 if not errorlevel 1 set "TESSERACT_FOUND=1"

REM Auto-detect common install locations
if %TESSERACT_FOUND%==0 (
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"
        set "TESSERACT_FOUND=1"
        echo [Tesseract] Auto-detected: C:\Program Files\Tesseract-OCR
    )
)

if %TESSERACT_FOUND%==0 (
    if exist "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe" (
        set "PATH=%PATH%;C:\Program Files (x86)\Tesseract-OCR"
        set "TESSERACT_FOUND=1"
        echo [Tesseract] Auto-detected: C:\Program Files (x86)\Tesseract-OCR
    )
)

if %TESSERACT_FOUND%==0 (
    if exist "D:\Tesseract-OCR\tesseract.exe" (
        set "PATH=%PATH%;D:\Tesseract-OCR"
        set "TESSERACT_FOUND=1"
        echo [Tesseract] Auto-detected: D:\Tesseract-OCR
    )
)

if %TESSERACT_FOUND%==0 (
    echo [WARNING] Tesseract OCR not found in PATH or common locations!
    echo Install from: https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo Press any key to continue anyway (OCR will be disabled)...
    pause >nul
)

REM --- CREATE VENV ---
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv!
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

REM --- INSTALL DEPS ---
echo [2/4] Checking dependencies...
python -m pip install --upgrade pip -q >nul 2>&1
pip install -r requirements.txt -q >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)

echo [3/4] Dependencies ready!
echo.

REM --- SETUP FOLDERS ---
set "SCRIPT_DIR=%~dp0"
set "INPUT_DIR=%SCRIPT_DIR%input"
set "OUTPUT_DIR=%SCRIPT_DIR%output"
set "ASSETS_DIR=%SCRIPT_DIR%assets"

if not exist "%INPUT_DIR%" mkdir "%INPUT_DIR%"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if not exist "%ASSETS_DIR%\music" mkdir "%ASSETS_DIR%\music"
if not exist "%ASSETS_DIR%\sound_effects" mkdir "%ASSETS_DIR%\sound_effects"

echo [4/4] Folders ready:
echo    Input : %INPUT_DIR%
echo    Output: %OUTPUT_DIR%
echo.

REM --- MENU ---
echo  ==========================================
echo   SELECT INPUT METHOD:
echo  ==========================================
echo   [1] Browse for video file (file picker)
echo   [2] Auto-scan INPUT folder
echo   [3] Drag and Drop mode
echo   [4] Open folders only
echo   [5] Exit
echo  ==========================================
echo.
set /p choice="Enter choice (1-5): "

if "%choice%"=="1" goto BROWSE
if "%choice%"=="2" goto AUTO_SCAN
if "%choice%"=="3" goto DRAG_DROP
if "%choice%"=="4" goto OPEN_FOLDERS
if "%choice%"=="5" exit /b 0
goto MENU

REM ==========================================
REM OPTION 1: FILE BROWSER
REM ==========================================
:BROWSE
echo.
echo [File Browser] Opening file picker...

set "PS_FILE=%TEMP%\picker.ps1"
(
echo Add-Type -AssemblyName System.Windows.Forms
echo $dlg = New-Object System.Windows.Forms.OpenFileDialog
echo $dlg.Title = 'Select COD Gameplay Video'
echo $dlg.Filter = 'Video Files^|*.mp4;*.avi;*.mkv;*.mov;*.wmv^|All Files^|*.*'
echo $dlg.InitialDirectory = '%INPUT_DIR%'
echo $dlg.Multiselect = $false
echo if ($dlg.ShowDialog() -eq 'OK') {
echo     $dlg.FileName ^| Out-File '%TEMP%\selected.txt' -Encoding utf8
echo } else {
echo     'CANCELLED' ^| Out-File '%TEMP%\selected.txt' -Encoding utf8
echo }
) > "%PS_FILE%"

powershell -ExecutionPolicy Bypass -NoProfile -File "%PS_FILE%"
del "%PS_FILE%" >nul 2>&1

if not exist "%TEMP%\selected.txt" (
    echo [ERROR] File picker failed!
    pause
    goto MENU
)

set /p VIDEO_PATH=<"%TEMP%\selected.txt"
del "%TEMP%\selected.txt" >nul 2>&1

if "%VIDEO_PATH%"=="CANCELLED" (
    echo [INFO] Cancelled by user.
    pause
    goto MENU
)

echo [SELECTED] %VIDEO_PATH%
goto PROCESS

REM ==========================================
REM OPTION 2: AUTO-SCAN INPUT FOLDER
REM ==========================================
:AUTO_SCAN
echo.
echo [Auto-Scan] Scanning INPUT folder...

set "FOUND_COUNT=0"
set "FILE_1="
set "FILE_2="
set "FILE_3="
set "FILE_4="
set "FILE_5="
set "FILE_6="
set "FILE_7="
set "FILE_8="
set "FILE_9="
set "FILE_10="

for %%E in (mp4 avi mkv mov wmv) do (
    for %%F in ("%INPUT_DIR%\*.%%E") do (
        if exist "%%F" (
            set /a FOUND_COUNT+=1
            set "FILE_!FOUND_COUNT!=%%F"
            echo   [!FOUND_COUNT!] %%~nxF
        )
    )
)

if %FOUND_COUNT%==0 (
    echo.
    echo [WARNING] No videos found in INPUT folder!
    echo Place videos in: %INPUT_DIR%
    echo.
    set /p opennow="Open INPUT folder now? (Y/N): "
    if /I "%opennow%"=="Y" explorer "%INPUT_DIR%"
    pause
    goto MENU
)

if %FOUND_COUNT%==1 (
    set "VIDEO_PATH=%FILE_1%"
    goto PROCESS
)

echo.
set /p vidnum="Enter video number: "

if "%vidnum%"=="1" set "VIDEO_PATH=%FILE_1%" & goto PROCESS
if "%vidnum%"=="2" set "VIDEO_PATH=%FILE_2%" & goto PROCESS
if "%vidnum%"=="3" set "VIDEO_PATH=%FILE_3%" & goto PROCESS
if "%vidnum%"=="4" set "VIDEO_PATH=%FILE_4%" & goto PROCESS
if "%vidnum%"=="5" set "VIDEO_PATH=%FILE_5%" & goto PROCESS
if "%vidnum%"=="6" set "VIDEO_PATH=%FILE_6%" & goto PROCESS
if "%vidnum%"=="7" set "VIDEO_PATH=%FILE_7%" & goto PROCESS
if "%vidnum%"=="8" set "VIDEO_PATH=%FILE_8%" & goto PROCESS
if "%vidnum%"=="9" set "VIDEO_PATH=%FILE_9%" & goto PROCESS
if "%vidnum%"=="10" set "VIDEO_PATH=%FILE_10%" & goto PROCESS

echo [ERROR] Invalid selection!
pause
goto MENU

REM ==========================================
REM OPTION 3: DRAG AND DROP
REM ==========================================
:DRAG_DROP
echo.
if "%~1"=="" (
    echo [INFO] Drag and drop a video file onto Start.bat
    echo        Or run: Start.bat "path\to\video.mp4"
    echo.
    pause
    goto MENU
)
set "VIDEO_PATH=%~1"
goto PROCESS

REM ==========================================
REM OPTION 4: OPEN FOLDERS
REM ==========================================
:OPEN_FOLDERS
echo.
echo Opening folders...
explorer "%INPUT_DIR%"
explorer "%OUTPUT_DIR%"
pause
goto MENU

REM ==========================================
REM PROCESS VIDEO
REM ==========================================
:PROCESS
echo.
echo  ==========================================
echo   PROCESSING VIDEO
echo   Input : %VIDEO_PATH%
echo   Output: %OUTPUT_DIR%
echo  ==========================================
echo.

for %%F in ("%VIDEO_PATH%") do set "VIDEO_NAME=%%~nF"
set "OUTPUT_FILE=%OUTPUT_DIR%\%VIDEO_NAME%_highlights_v3.mp4"

REM Check for music
set "MUSIC_ARG="
for %%E in (mp3 wav) do (
    for %%M in ("%ASSETS_DIR%\music\*.%%E") do (
        if exist "%%M" (
            set "MUSIC_ARG=--music "%%M""
            echo [Music] Found: %%~nxM
            goto MUSIC_DONE
        )
    )
)
:MUSIC_DONE

set "INTRO_ARG="
if exist "%ASSETS_DIR%\music\intro.mp3" set "INTRO_ARG=--intro-music "%ASSETS_DIR%\music\intro.mp3""

set "OUTRO_ARG="
if exist "%ASSETS_DIR%\music\outro.mp3" set "OUTRO_ARG=--outro-music "%ASSETS_DIR%\music\outro.mp3""

echo.
echo Starting processing...
echo.

python main.py "%VIDEO_PATH%" --output "%OUTPUT_FILE%" --tiktok --individual %MUSIC_ARG% %INTRO_ARG% %OUTRO_ARG%

echo.
if exist "%OUTPUT_FILE%" (
    echo SUCCESS! Saved: %OUTPUT_FILE%
    for %%F in ("%OUTPUT_FILE%") do echo Size: %%~zF bytes
    echo.
    set /p openout="Open OUTPUT folder? (Y/N): "
    if /I "%openout%"=="Y" explorer "%OUTPUT_DIR%"
) else (
    echo ERROR: Processing failed or no events detected.
    echo Check temp folder for logs.
)

echo.
echo Press any key to return to menu...
pause >nul
goto MENU
