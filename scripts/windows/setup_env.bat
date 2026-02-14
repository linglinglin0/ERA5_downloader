@echo off
REM ERA5下载软件 - Python环境配置脚本
echo ========================================
echo    ERA5下载软件 - 环境配置脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 检测到Python版本:
python --version
echo.

REM 创建虚拟环境
echo [2/4] 创建虚拟环境...
cd /d "%~dp0"
if exist venv (
    echo 虚拟环境已存在，删除旧的...
    rmdir /s /q venv
)
python -m venv venv
if errorlevel 1 (
    echo [错误] 虚拟环境创建失败
    pause
    exit /b 1
)
echo 虚拟环境创建成功！
echo.

REM 激活虚拟环境并安装依赖
echo [3/4] 激活虚拟环境并安装依赖包...
call venv\Scripts\activate.bat

echo 升级pip...
python -m pip install --upgrade pip

echo.
echo 安装项目依赖...
pip install -r requirements.txt
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
echo 1. 双击运行 "启动程序.bat"
echo 2. 或手动执行: venv\Scripts\activate.bat
echo    然后运行: python ERA5download_GUI_v2.py
echo ========================================
echo.
pause
