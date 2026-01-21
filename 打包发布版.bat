@echo off
chcp 65001 >nul
echo ========================================
echo ERA5 下载器 - 一键打包脚本
echo 版本: v2.1
echo ========================================
echo.

REM 设置变量
set VERSION=v2.1
set APP_NAME=ERA5下载器
set RELEASE_DIR=release

REM 检查是否存在release目录
if exist "%RELEASE_DIR%" (
    echo 警告: release目录已存在
    echo 是否删除并重新创建? (Y/N)
    set /p confirm=
    if /i "%confirm%"=="Y" (
        echo 删除旧的release目录...
        rmdir /s /q "%RELEASE_DIR%"
    ) else (
        echo 取消打包
        pause
        exit /b 0
    )
)

REM 创建发布目录
echo [1/4] 创建发布目录...
mkdir "%RELEASE_DIR%" 2>nul
cd "%RELEASE_DIR%"
mkdir "%APP_NAME%-%VERSION%" 2>nul

REM 复制核心文件
echo [2/4] 复制核心文件...
copy "..\ERA5download_GUI_v2.py" "%APP_NAME%-%VERSION%\" >nul
if errorlevel 1 (
    echo 错误: 无法找到主程序文件！
    pause
    exit /b 1
)

copy "..\requirements.txt" "%APP_NAME%-%VERSION%\" >nul
if errorlevel 1 (
    echo 警告: requirements.txt 不存在，将创建默认版本
    echo customtkinter^>=5.0.0 > "%APP_NAME%-%VERSION%\requirements.txt"
    echo boto3^>=1.28.0 >> "%APP_NAME%-%VERSION%\requirements.txt"
)

REM 复制文档文件
echo [3/4] 复制文档文件...
copy "..\README.md" "%APP_NAME%-%VERSION%\" >nul 2>&1
copy "..\新功能使用说明.md" "%APP_NAME%-%VERSION%\" >nul 2>&1
copy "..\断点续传快速使用指南.md" "%APP_NAME%-%VERSION%\" >nul 2>&1

REM 创建快速开始文件
echo # ERA5 下载器 - 快速开始 > "%APP_NAME%-%VERSION%\快速开始.txt"
echo. >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo ## 安装步骤 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo. >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo 1. 确保已安装 Python 3.8 或更高版本 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo 2. 安装依赖包: >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo    pip install -r requirements.txt >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo 3. 运行程序: >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo    python ERA5download_GUI_v2.py >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo. >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo ## 首次使用 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo. >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo 1. 输入日期 (YYYYMM格式，例如: 202510) >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo 2. 选择保存路径 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo 3. 勾选需要下载的变量 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo 4. 点击"开始下载" >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo. >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo ## 新功能 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo. >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo - 断点续传: 支持从中断位置继续下载 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo - 自动重试: 网络错误时自动重试3次 >> "%APP_NAME%-%VERSION%\快速版本.txt"
echo - 配置记忆: 记住日期、路径、变量选择 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo - 实时百分比: 显示详细的下载进度 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo. >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo ## 详细文档 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo. >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo - 查看 README.md 了解完整功能 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo - 查看 新功能使用说明.md 了解新功能 >> "%APP_NAME%-%VERSION%\快速开始.txt"
echo - 查看 断点续传快速使用指南.md 了解续传功能 >> "%APP_NAME%-%VERSION%\快速开始.txt"

REM 创建压缩包
echo [4/4] 创建压缩包...
cd ..
powershell -Command "Compress-Archive -Path '%RELEASE_DIR%\%APP_NAME%-%VERSION%' -DestinationPath '%APP_NAME%-%VERSION%-源代码版.zip' -Force"

if errorlevel 1 (
    echo.
    echo 错误: 创建压缩包失败！
    echo 可能是因为文件正在被占用...
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ 打包完成！
echo ========================================
echo.
echo 输出文件: %APP_NAME%-%VERSION%-源代码版.zip
echo 发布目录: %RELEASE_DIR%\%APP_NAME%-%VERSION%\
echo.
echo 文件清单:
dir /b "%RELEASE_DIR%\%APP_NAME%-%VERSION%\"
echo.
echo 📦 压缩包大小:
for %%F in ("%APP_NAME%-%VERSION%-源代码版.zip") do echo %%~zF 字节
echo.
echo 可以将 %APP_NAME%-%VERSION%-源代码版.zip 分发给其他用户
echo.
pause
