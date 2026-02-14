@echo off
REM ERA5下载软件 - 使用uv配置环境
echo ========================================
echo    ERA5下载软件 - UV环境配置脚本
echo ========================================
echo.

REM 设置临时PATH
set "PATH=C:\Users\Administrator\.local\bin;%PATH%"

REM 检查uv是否安装
uv --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到uv，请先安装uv
    echo 安装命令: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

echo [1/4] 检测到uv版本:
uv --version
echo.

REM 进入项目目录
cd /d "%~dp0"

REM 初始化项目（如果还没有pyproject.toml）
echo [2/4] 初始化uv项目...
if not exist pyproject.toml (
    uv init --no-readme
    echo 项目初始化完成
) else (
    echo 项目已存在，跳过初始化
)
echo.

REM 添加依赖
echo [3/4] 添加项目依赖包...
uv add customtkinter "boto3>=1.28.0" "botocore>=1.31.0"
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo.

echo [4/4] 环境配置完成！
echo.
echo ========================================
echo 使用方法:
echo 1. 双击运行 "启动程序_uv.bat"
echo 2. 或手动执行:
echo    uv run python ERA5download_GUI_v2.py
echo ========================================
echo.
pause
