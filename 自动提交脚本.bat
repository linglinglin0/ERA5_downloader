@echo off
chcp 65001 >nul
echo ================================================================================
 ERA5下载器 - 自动化Git提交脚本
 ================================================================================
 echo.

REM 检查是否在正确的目录
if not exist "ERA5download_GUI_v2.py" (
    echo [错误] 请在ERA5下载软件根目录下运行此脚本
    pause
    exit /b 1
)

echo [信息] 当前目录: %CD%
echo.

REM 检查git状态
echo [步骤1/6] 检查Git状态...
git status
echo.

echo ================================================================================
 echo  请选择要执行的提交方案：
 echo ================================================================================
 echo.
 echo 1. 只提交主分支的基础改进
 echo 2. 提交 v2.1 自动重启功能（到新分支）
 echo 3. 提交高级特性集成（到新分支）
 echo 4. 完整提交：基础改进 + v2.1 + 高级特性
 echo 5. 查看详细提交计划
 echo 6. 退出
 echo.
 set /p CHOICE="请选择 (1-6): "

if "%CHOICE%"=="1" goto COMMIT_BASIC
if "%CHOICE%"=="2" goto COMMIT_V2_RESTART
if "%CHOICE%"=="3" goto COMMIT_ADVANCED
if "%CHOICE%"=="4" goto COMMIT_ALL
if "%CHOICE%"=="5" goto SHOW_PLAN
if "%CHOICE%"=="6" goto END

echo [错误] 无效选择
pause
exit /b 1

:COMMIT_BASIC
echo.
echo ================================================================================
 echo 提交主分支的基础改进
echo ================================================================================
 echo.
echo [提交] 更新项目依赖...
git add pyproject.toml requirements.txt uv.lock
git commit -m "build: 更新项目依赖到uv包管理器和CustomTkinder

- 迁移到 uv 包管理器
- 更新 CustomTkinter 到最新版本
- 添加项目配置文件
"
if errorlevel 1 goto ERROR
echo [成功] 基础改进已提交
goto END

:COMMIT_V2_RESTART
echo.
echo ================================================================================
 echo 提交 v2.1 自动重启功能
echo ================================================================================
 echo.
echo [步骤1/3] 创建并切换到 feature/auto-restart-v2 分支...
git checkout -b feature/auto-restart-v2
if errorlevel 1 goto ERROR

echo.
echo [步骤2/3] 添加v2.1功能文件...
git add ERA5download_GUI_v2_auto_restart.py
git add "启动v2自动重启版.bat"
git add "v2.1智能自动重启更新说明.md"
git add "v2.1完全自动重启功能完成.md"
git add "v2.1时间计算Bug修复说明.md"
git add "v2.1自动重启卡死Bug修复说明.md"
git add "v2.1自动重启卡死最终修复.md"

git commit -m "feat(v2.1): 添加智能自动重启版下载器及相关功能

核心功能：
- 基于v2_fixed版本，保留所有性能修复
- 内置速度监控，实时检测下载速度
- 智能低速检测：速度 ^< 500 KB/s 持续120秒自动重启
- 断点续传无缝恢复
- 完全自动化：无需手动确认，支持重启后自动开始下载
- 防卡死优化：在守护线程中执行重启，避免GUI阻塞

技术实现：
- 使用 threading.Thread 守护线程执行重启
- 优雅退出机制：self.quit() + sys.exit()
- 标志文件机制：.era5_auto_start_flag
- 重启统计和日志记录

相关文件：
- ERA5download_GUI_v2_auto_restart.py (主程序)
- 启动v2自动重启版.bat (启动脚本)
- v2.1相关文档 (完整的使用和修复说明)
"
if errorlevel 1 goto ERROR

echo.
echo [步骤3/3] 推送到远程...
git push -u origin feature/auto-restart-v2
if errorlevel 1 goto ERROR

echo.
echo [成功] v2.1自动重启功能已提交到 feature/auto-restart-v2 分支
goto END

:COMMIT_ADVANCED
echo.
echo ================================================================================
 echo 提交高级特性集成功能
echo ================================================================================
 echo.
echo [步骤1/5] 创建并切换到 feature/advanced-features-v2 分支...
git checkout master
git checkout -b feature/advanced-features-v2
if errorlevel 1 goto ERROR

echo.
echo [步骤2/5] 添加性能监控器...
git add era5_performance_monitor.py "启动性能监控.bat"
git commit -m "feat(monitor): 添加性能监控器GUI应用

核心功能：
- 实时监控下载速度和累计下载量
- SQLite数据库持久化存储
- 三种图表：速度曲线、累计下载量、系统资源
- 双Y轴显示（GB/MB）
- 智能单位格式化
- 网络接口I/O监控
"
if errorlevel 1 goto ERROR

echo.
echo [步骤3/5] 添加v3.0和v3.1功能...
git add ERA5download_GUI_v3.py "启动程序_v3.bat"
git add "v3.0新功能说明.md" "v3.0性能优化说明.md"
git commit -m "feat(v3.0): 添加高级特性集成版下载器"
if errorlevel 1 goto ERROR

echo.
echo [步骤4/5] 添加v3.1独立监控版...
git add ERA5_AutoRecovery.py "启动智能恢复版.bat"
git add "智能自动恢复功能说明.md"
git commit -m "feat(v3.1): 添加独立智能自动恢复系统"
if errorlevel 1 goto ERROR

echo.
echo [步骤5/5] 推送到远程...
git push -u origin feature/advanced-features-v2
if errorlevel 1 goto ERROR

echo.
echo [成功] 高级特性功能已提交到 feature/advanced-features-v2 分支
goto END

:COMMIT_ALL
echo.
echo ================================================================================
 echo 完整提交：基础改进 + v2.1 + 高级特性
echo ================================================================================
 echo.
echo [警告] 这将执行所有提交，包括创建多个分支
echo.
set /p CONFIRM="确定要继续吗？(y/n): "
if /i not "%CONFIRM%"=="y" goto END

echo.
echo [阶段1/4] 提交主分支基础改进...
git add pyproject.toml requirements.txt uv.lock
git commit -m "build: 更新项目依赖到uv包管理器和CustomTkinter"
git push origin master
if errorlevel 1 goto ERROR

echo.
echo [阶段2/4] 提交v2.1自动重启功能...
git checkout -b feature/auto-restart-v2
git add ERA5download_GUI_v2_auto_restart.py "启动v2自动重启版.bat"
git add v2.1*.md
git commit -m "feat(v2.1): 添加智能自动重启版下载器"
git push -u origin feature/auto-restart-v2
if errorlevel 1 goto ERROR

echo.
echo [阶段3/4] 提交高级特性集成功能...
git checkout master
git checkout -b feature/advanced-features-v2
git add era5_performance_monitor.py "启动性能监控.bat"
git commit -m "feat(monitor): 添加性能监控器"
git add ERA5download_GUI_v3.py "启动程序_v3.bat"
git add v3.0*.md
git commit -m "feat(v3.0): 添加高级特性集成版"
git add ERA5_AutoRecovery.py "启动智能恢复版.bat"
git add "智能自动恢复功能说明.md"
git commit -m "feat(v3.1): 添加独立智能自动恢复系统"
git push -u origin feature/advanced-features-v2
if errorlevel 1 goto ERROR

echo.
echo [阶段4/4] 提交主分支文档和工具...
git checkout master
git add README_总览.md 版本总览README.md "UV包管理器使用指南.md"
git commit -m "docs: 添加项目总览文档"
git add setup_env*.bat create_release*.py check_*.py diagnostic_tool.py
git commit -m "tools: 添加项目工具脚本"
git add "启动"*.bat
git commit -m "feat: 添加所有版本的启动脚本"
git push origin master
if errorlevel 1 goto ERROR

echo.
echo [成功] 所有功能已提交！
goto END

:SHOW_PLAN
echo.
echo ================================================================================
 echo 详细提交计划
 echo ================================================================================
 echo.
echo 请查看 "GIT提交计划.md" 文件获取完整的提交计划
 echo.
 echo 主要内容：
 echo   - 两个功能分支：
 echo     1. feature/auto-restart-v2 (v2.1智能自动重启)
 echo     2. feature/advanced-features-v2 (高级特性集成)
 echo   - 每个分支包含多个提交
 echo   - 详细的commit message和文件列表
 echo.
pause
goto END

:ERROR
echo.
echo [错误] Git操作失败，请检查错误信息
echo.
pause
exit /b 1

:END
echo.
echo ================================================================================
 echo 提交完成！
 echo ================================================================================
 echo.
echo 分支状态：
 git branch -a
 echo.
echo 远程状态：
 git remote -v
 echo.
pause
