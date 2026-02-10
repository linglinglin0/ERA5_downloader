@echo off
chcp 65001 >nul
echo ================================================================================
echo                       ERA5下载性能监控器
echo ================================================================================
echo.
echo 功能：
echo - 实时下载速度监控（折线图）
echo - 累计下载量曲线
echo - 系统资源使用监控
echo - 数据持久化存储
echo - 统计分析报告
echo - 数据导出（CSV格式）
echo.
echo 按任意键启动...
pause >nul
echo.
echo [信息] 正在启动性能监控器...
echo.
cd /d "%~dp0"

REM 检查matplotlib是否安装
python -c "import matplotlib" 2>nul
if errorlevel 1 (
    echo [信息] matplotlib未安装，正在安装...
    uv add matplotlib
)

echo [信息] 启动中...
echo.

uv run era5_performance_monitor.py

echo.
pause
