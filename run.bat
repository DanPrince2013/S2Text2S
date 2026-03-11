@echo off
REM S2Text2S — launch the application
REM Must be run as Administrator for global hotkeys to work.
echo Starting S2Text2S...
python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo S2Text2S exited with an error.  See output above for details.
    pause
)
