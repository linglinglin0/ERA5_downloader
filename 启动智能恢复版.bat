@echo off
chcp 65001 >nul
echo ================================================================================
 ERA5下载器 v3.1 - 智能自动恢复版
 ================================================================================
 echo.
 echo 新功能：
 echo - 实时监控下载速度
 echo - 检测速度持续下降（低于500 KB/s并持续30秒）
 echo - 自动重启下载软件
 echo - 利用断点续传无缝恢复
 echo.
 echo 使用方法：
 echo 1. 本脚本会自动启动 ERA5download_GUI_v3.py
 echo 2. 在下载器中配置参数并开始下载
 echo 3. 后台自动监控速度，自动重启
 echo.
 echo ================================================================================
 echo.
 echo [配置选项]
 echo.
 set /p LOW_SPEED="请输入低速阈值 (KB/s) [默认: 500]: "
 set /p DURATION="请输入持续时间 (秒) [默认: 30]: "
 set /p AUTO_START="是否自动开始下载？(y/n) [默认: n]: "
 echo.

 REM 设置默认值
 if "%LOW_SPEED%"=="" set LOW_SPEED=500
 if "%DURATION%"=="" set DURATION=30
 if "%AUTO_START%"=="" set AUTO_START=n

 REM 保存配置
 echo {> ".era5_auto_recovery_config.json"
 echo   "low_speed_kb": %LOW_SPEED%,>> ".era5_auto_recovery_config.json"
 echo   "duration_sec": %DURATION%,>> ".era5_auto_recovery_config.json"
 if "%AUTO_START%"=="y" (
     echo   "auto_start": true>> ".era5_auto_recovery_config.json"
 ) else (
     echo   "auto_start": false>> ".era5_auto_recovery_config.json"
 )
 echo }>> ".era5_auto_recovery_config.json"

 echo [配置已保存]
 echo   速度阈值: %LOW_SPEED% KB/s
 echo   持续时间: %DURATION% 秒
 echo   自动开始: %AUTO_START%
 echo.
 echo 按任意键启动...
 pause >nul
 echo.

 cd /d "%~dp0"

 echo [信息] 正在启动智能恢复版下载器...
 echo.

 uv run ERA5_AutoRecovery.py

 echo.
 pause
