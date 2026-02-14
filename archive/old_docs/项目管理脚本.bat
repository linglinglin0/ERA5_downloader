@echo off
chcp 65001 >nul
echo ================================================================================
echo                          ERA5下载软件 - 项目管理
echo ================================================================================
echo.
echo 请选择操作:
echo.
echo [1] 检查Release状态
echo [2] 创建新Release
echo [3] 删除Release
echo [4] 查看代码审查报告
echo [5] 查看性能分析报告
echo [6] 查看发布总结
echo [7] 运行诊断工具
echo [8] 分析错误日志
echo [0] 退出
echo.
set /p choice="请输入选项 (0-8): "

if "%choice%"=="1" (
    echo.
    echo [信息] 正在检查Release状态...
    echo.
    uv run check_releases.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo [信息] 创建新Release...
    echo.
    uv run create_release_clean.py
    pause
) else if "%choice%"=="3" (
    echo.
    set /p tag="请输入要删除的版本号 (如 v1.0.0): "
    set /p token="请输入GitHub Token: "
    uv run deleteRelease.py %token% %tag%
    pause
) else if "%choice%"=="4" (
    start CODE_REVIEW_REPORT.md
) else if "%choice%"=="5" (
    start 性能问题分析报告.md
) else if "%choice%"=="6" (
    start 发布总结.md
) else if "%choice%"=="7" (
    echo.
    echo [信息] 启动诊断工具...
    echo.
    uv run diagnostic_tool.py
    pause
) else if "%choice%"=="8" (
    echo.
    echo [信息] 分析错误日志...
    echo.
    uv run log_analyzer.py
    pause
) else if "%choice%"=="0" (
    echo.
    echo [退出] 已退出
    exit
) else (
    echo.
    echo [错误] 无效选项
    pause
)
