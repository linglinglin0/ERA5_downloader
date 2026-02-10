@echo off
REM ERA5下载软件 - 启动脚本
cd /d "%~dp0"

REM 检查虚拟环境是否存在
if not exist venv (
    echo [错误] 虚拟环境不存在！
    echo 请先运行 "setup_env.bat" 配置环境
    pause
    exit /b 1
)

REM 激活虚拟环境并启动程序
call venv\Scripts\activate.bat
echo 正在启动ERA5下载软件...
python ERA5download_GUI_v2.py

pause
