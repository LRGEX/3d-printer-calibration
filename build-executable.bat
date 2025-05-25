@echo off
title Building 3D Printer Calibration Utility
echo.
echo ===============================================
echo   Building 3D Printer Calibration Utility
echo ===============================================
echo.

REM Change to project directory
cd /d "%~dp0"

REM Activate virtual environment and build
echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Building executable with PyInstaller...
pyinstaller --onefile --console --icon="assetsigx-dark-icon.ico" --name="3D-Printer-Calibration-v2.0" app.py

echo.
echo Build complete! Check the dist\ folder for the executable.
echo.
echo Press any key to continue...
pause >nul
