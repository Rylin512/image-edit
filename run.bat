@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "scripts\launch.py" %*
) else (
    python "scripts\launch.py" %*
)

if errorlevel 1 (
    echo.
    echo Startup failed. Review the message above, then try again.
    pause
)
endlocal
