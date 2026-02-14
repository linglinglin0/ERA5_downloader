@echo off
REM ========================================
REM ERA5 数据下载工具 - 打包脚本
REM ========================================

echo.
echo ========================================
echo ERA5 数据下载工具 - 打包工具
echo ========================================
echo.

REM 检查环境
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 环境正常

REM 检查 PyInstaller
echo [2/5] 检查 PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装 PyInstaller...
    pip install pyinstaller>=6.0.0
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        pause
        exit /b 1
    )
)
echo [OK] PyInstaller 已安装

REM 清理旧的打包文件
echo [3/5] 清理旧文件...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
echo [OK] 已清理

REM 开始打包
echo [4/5] 开始打包（这可能需要几分钟）...
echo.
python -m PyInstaller era5_downloader.spec --clean

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

REM 打包完成
echo.
echo [5/5] 打包完成！
echo.
echo ========================================
echo 输出位置: dist\era5_downloader\
echo ========================================
echo.
echo 文件夹内容:
dir /b dist\era5_downloader\
echo.
echo 主程序: ERA5数据下载工具.exe
echo.

REM 询问是否打开输出文件夹
set /p open_folder="是否打开输出文件夹？ (Y/N): "
if /i "%open_folder%"=="Y" (
    explorer dist\era5_downloader
)

echo.
echo 打包成功！可以将 dist\era5_downloader 文件夹分发给用户
echo.
pause
