@echo off
REM ERA5下载软件 - 使用uv启动
cd /d "%~dp0"

REM 添加uv到PATH
set "PATH=C:\Users\Administrator\.local\bin;%PATH%"

REM 检查uv是否安装
uv --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到uv，请先安装uv
    pause
    exit /b 1
)

REM 使用uv运行程序
echo 正在启动ERA5下载软件...
echo.
uv run python ERA5download_GUI_v2.py

pause
