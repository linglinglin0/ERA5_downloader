@echo off
REM ERA5下载软件 - UV启动脚本（简化版）
cd /d "%~dp0"

echo ========================================
echo    ERA5下载软件 - 启动中...
echo ========================================
echo.

REM 使用完整路径调用UV
"C:\Users\Administrator\.local\bin\uv.exe" run python ERA5download_GUI_v2.py

if errorlevel 1 (
    echo.
    echo [错误] 程序运行失败
    pause
)
