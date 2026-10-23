@echo off
setlocal
chcp 65001 >nul
title Gerando YouTubeMP3.exe
cd /d "%~dp0"

echo === Gerando YouTubeMP3.exe ===
echo.

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "youtube_mp3_gui.py" (
    echo ERRO: youtube_mp3_gui.py nao esta nesta pasta.
    pause
    exit /b 1
)

if not exist "ffmpeg.exe" (
    echo ERRO: ffmpeg.exe nao esta nesta pasta.
    pause
    exit /b 1
)

if not exist "ffprobe.exe" (
    echo ERRO: ffprobe.exe nao esta nesta pasta.
    pause
    exit /b 1
)

if not exist "%PYTHON%" (
    echo ERRO: ambiente Python do projeto nao encontrado em .venv.
    echo Crie o ambiente e instale yt-dlp e pyinstaller antes de continuar.
    pause
    exit /b 1
)

"%PYTHON%" -c "import yt_dlp, PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo ERRO: yt-dlp ou PyInstaller nao esta instalado no ambiente .venv.
    echo Instale com: "%PYTHON%" -m pip install yt-dlp pyinstaller
    pause
    exit /b 1
)

if exist "dist\YouTubeMP3.exe" del /q "dist\YouTubeMP3.exe"

"%PYTHON%" -m PyInstaller --clean --noconfirm --onefile --windowed --name YouTubeMP3 ^
    --add-binary "ffmpeg.exe;." ^
    --add-binary "ffprobe.exe;." ^
    --collect-all yt_dlp ^
    youtube_mp3_gui.py

if errorlevel 1 (
    echo ERRO ao gerar o executavel.
    pause
    exit /b 1
)

echo.
echo Pronto! Executavel unico gerado em: dist\YouTubeMP3.exe
echo Copie somente esse .exe para usar. O usuario escolhe o arquivo .txt pela interface.
pause
