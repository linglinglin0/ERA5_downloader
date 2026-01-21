@echo off
chcp 65001 >nul
echo ========================================
echo ERA5 下载器 - Windows可执行文件打包脚本
echo 版本: v2.1
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python环境！
    echo 请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 检查PyInstaller
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller未安装，正在安装...
    pip install pyinstaller
    if errorlevel 1 (
        echo 错误: PyInstaller安装失败！
        pause
        exit /b 1
    )
)

REM 设置变量
set VERSION=v2.1
set APP_NAME=ERA5下载器
set MAIN_FILE=ERA5download_GUI_v2.py

REM 检查主程序文件
if not exist "%MAIN_FILE%" (
    echo 错误: 未找到主程序文件 %MAIN_FILE%
    pause
    exit /b 1
)

REM 清理旧的构建
echo [1/6] 清理旧的构建文件...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
if exist *.spec del /q *.spec 2>nul

REM 使用PyInstaller打包
echo [2/6] 使用PyInstaller打包程序...
echo 这可能需要几分钟时间...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "%APP_NAME%-%VERSION%" ^
    --clean ^
    --noconfirm ^
    --add-data "README.md;." ^
    "%MAIN_FILE%"

if errorlevel 1 (
    echo.
    echo 错误: PyInstaller打包失败！
    echo 请检查错误信息
    pause
    exit /b 1
)

echo [3/6] 复制文档文件到dist目录...
if exist README.md copy README.md dist\ >nul
if exist 新功能使用说明.md copy "新功能使用说明.md" dist\ >nul
if exist 断点续传快速使用指南.md copy "断点续传快速使用指南.md" dist\ >nul

REM 创建使用说明
echo [4/6] 创建使用说明文件...
(
echo ERA5 下载器 - Windows可执行版 v2.1
echo.
echo ========================================
echo 快速开始
echo ========================================
echo.
echo 1. 双击运行 ERA5下载器-v2.1.exe
echo.
echo 2. 首次使用：
echo    - 输入日期（YYYYMM格式，如：202510）
echo    - 选择保存路径
echo    - 勾选需要下载的变量
echo    - 点击"开始下载"
echo.
echo 3. 新功能：
echo    ✓ 断点续传 - 支持从中断位置继续下载
echo    ✓ 自动重试 - 网络错误时自动重试3次
echo    ✓ 配置记忆 - 记住日期、路径、变量选择
echo    ✓ 实时百分比 - 显示详细的下载进度
echo.
echo ========================================
echo 详细文档
echo ========================================
echo.
echo - README.md - 完整功能说明
echo - 新功能使用说明.md - 新功能介绍
echo - 断点续传快速使用指南.md - 断点续传指南
echo.
echo ========================================
echo 常见问题
echo ========================================
echo.
echo Q: 杀毒软件报警？
echo A: 这是误报，可以添加到信任列表
echo.
echo Q: 程序无法启动？
echo A: 检查是否被防火墙阻止，或以管理员身份运行
echo.
echo Q: 下载速度慢？
echo A: 调整线程数滑块，建议5-8个线程
echo.
echo ========================================
echo 系统要求
echo ========================================
echo.
echo - Windows 7/8/10/11
echo - 网络连接
echo - 磁盘空间（根据下载数据量）
echo.
echo 技术支持: 如遇问题请查看文档
echo.
) > dist\使用说明.txt

REM 创建版本信息文件
echo [5/6] 创建版本信息文件...
(
echo ERA5 下载器 - 版本信息
echo.
echo 版本: v2.1
echo 发布日期: 2026-01-19
echo.
echo 主要功能:
echo - ERA5数据批量下载
echo - 断点续传支持
echo - 自动重试机制
echo - 配置自动记忆
echo - 实时进度显示
echo.
echo 技术栈:
echo - Python 3.8+
echo - CustomTkinter (GUI框架)
echo - Boto3 (AWS SDK)
echo.
echo 许可: 自由使用和分发
) > dist\版本信息.txt

REM 打包成ZIP
echo [6/6] 创建发布压缩包...
powershell -Command "Compress-Archive -Path 'dist\*' -DestinationPath '%APP_NAME%-%VERSION%-Windows.zip' -Force"

if errorlevel 1 (
    echo.
    echo 警告: 创建压缩包失败！
    echo 但可执行文件已生成在 dist 目录
    echo.
)

REM 显示结果
echo.
echo ========================================
echo ✅ 打包完成！
echo ========================================
echo.
echo 输出文件:
echo   - %APP_NAME%-%VERSION%-Windows.zip (发布包)
echo   - dist\%APP_NAME%-%VERSION%.exe (可执行文件)
echo.
echo 文件大小:
for %%F in ("dist\%APP_NAME%-%VERSION%.exe") do (
    set size=%%~zF
    set /a sizeMB=%%~zF/1024/1024
    echo   可执行文件: !sizeMB! MB
)

for %%F in ("%APP_NAME%-%VERSION%-Windows.zip") do (
    set size=%%~zF
    set /a sizeMB=%%~zF/1024/1024
    echo   压缩包: !sizeMB! MB
)

echo.
echo dist目录内容:
dir /b dist\
echo.
echo 可以将 %APP_NAME%-%VERSION%-Windows.zip 分发给其他用户
echo 用户无需安装Python环境，直接运行即可
echo.
pause
