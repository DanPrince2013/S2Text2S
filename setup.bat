@echo off
REM S2Text2S — one-time setup for Windows
echo Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo Installation failed. Make sure Python 3.10+ is installed and on PATH.
    pause
    exit /b 1
)
echo.
echo Setup complete!  Run "run.bat" to start S2Text2S.
pause
