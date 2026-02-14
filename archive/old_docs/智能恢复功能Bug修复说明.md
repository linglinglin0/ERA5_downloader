# 智能自动恢复功能 - Bug修复说明

## 修复时间
2026-02-10

---

## 🔧 修复的Bug列表

### Bug 1: 变量名错误导致程序崩溃 ⚠️ **严重**

**位置**: `ERA5_AutoRecovery.py:351`

**问题**:
```python
# 错误代码
low_speed_kb = input("请输入低速阈值 (KB/s) [默认: 500]: ").strip()
low_speed_threshold = int(low_speed) * 1024 if low_speed_kb else 500 * 1024
                              ^^^^^^^^^^
                              变量未定义！应该是 low_speed_kb
```

**影响**: 程序在获取用户输入时会立即崩溃，提示 `NameError: name 'low_speed' is not defined`

**修复**:
```python
# 修复后
low_speed_kb = input("请输入低速阈值 (KB/s) [默认: 500]: ").strip()
low_speed_threshold = int(low_speed_kb) * 1024 if low_speed_kb else 500 * 1024
                              ^^^^^^^^^^^
                              使用正确的变量名
```

---

### Bug 2: 缺少必要的Windows API导入 ⚠️ **严重**

**位置**:
- `ERA5_AutoRecovery.py:249` (stop_downloader函数)
- `ERA5_AutoRecovery.py:309` (auto_start_download函数)

**问题**:
```python
# 错误代码
def stop_downloader(self):
    # ... 省略 ...
    hwnd = win32gui.FindWindow("CTkTk", "ERA5 下载器")
           ^^^^^^^^^
           未导入！会导致 NameError
```

**影响**:
- 当尝试停止下载器时会崩溃
- 当尝试自动开始下载时会崩溃

**修复**:
```python
# 在文件开头添加统一导入
import os
import sys
import time
import json
import ctypes
import threading
import subprocess
from datetime import datetime
from pathlib import Path

# Windows API导入（延迟导入，避免在非Windows系统出错）
try:
    import win32gui
    import win32api
    import win32con
    import win32event
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("[警告] pywin32未安装，部分Windows功能将不可用")
```

同时更新函数以检查API可用性：
```python
def stop_downloader(self):
    if self.downloader_process:
        try:
            if WIN32_AVAILABLE:  # 检查API是否可用
                # 使用Windows API
            else:
                print("[AutoRecovery] Windows API不可用，将直接终止进程")
```

---

### Bug 3: JSON配置文件格式错误 ⚠️ **中等**

**位置**: `启动智能恢复版.bat:32-42`

**问题**:
```batch
REM 错误代码
echo {> ".era5_auto_recovery_config.json"
echo   "low_speed_kb": %LOW_SPEED%,>> ".era5_auto_recovery_config.json"
echo   "duration_sec": %DURATION%,>> ".era5_auto_recovery_config.json"
echo   "auto_start": false>> ".era5_auto_recovery_config.json"
echo }>> ".era5_auto_recovery_config.json"

REM 这里会导致问题！
if "%AUTO_START%"=="y" (
    echo   "auto_start": true>> ".era5_auto_recovery_config.json"
)
```

**生成的JSON**:
```json
{
  "low_speed_kb": 500,
  "duration_sec": 30,
  "auto_start": false
}
  "auto_start": true    ← 错误！重复的键，格式错误
}
```

**影响**:
- JSON文件格式错误，无法被Python正确解析
- 配置读取失败
- 程序可能使用默认值而非用户输入的值

**修复**:
```batch
REM 修复后的代码
echo {> ".era5_auto_recovery_config.json"
echo   "low_speed_kb": %LOW_SPEED%,>> ".era5_auto_recovery_config.json"
echo   "duration_sec": %DURATION%,>> ".era5_auto_recovery_config.json"
if "%AUTO_START%"=="y" (
    echo   "auto_start": true>> ".era5_auto_recovery_config.json"
) else (
    echo   "auto_start": false>> ".era5_auto_recovery_config.json"
)
echo }>> ".era5_auto_recovery_config.json"
```

---

### Bug 4: 窗口查找不健壮 ⚠️ **轻微**

**位置**: `ERA5_AutoRecovery.py:249, 309`

**问题**:
```python
# 只查找一个窗口标题
hwnd = win32gui.FindWindow("CTkTk", "ERA5 下载器")
```

**影响**:
- 如果v3.0的窗口标题变化（如增加了版本号），无法找到窗口
- 自动恢复功能无法正常工作

**修复**:
```python
# 尝试多种可能的窗口标题
hwnd = None
for title in ["ERA5 下载器 v3.0", "ERA5 下载器", "ERA5 Download Manager"]:
    hwnd = win32gui.FindWindow("CTkTk", title)
    if hwnd:
        print(f"[AutoRecovery] 找到下载器窗口: {title}")
        break
```

---

## ✅ 修复后的改进

### 1. 跨平台兼容性
- 增加了 `WIN32_AVAILABLE` 标志
- 在Windows API不可用时优雅降级
- 避免在非Windows系统上导入Windows特定模块

### 2. 更好的错误处理
- 所有函数都增加了 try-except 块
- 使用 `traceback.print_exc()` 输出详细错误信息
- 在API不可用时给出明确的提示

### 3. 更健壮的窗口查找
- 尝试多个可能的窗口标题
- 找到窗口后打印确认信息
- 找不到时给出清晰的提示

### 4. 更安全的进程终止
```python
# 修复前
self.downloader_process.wait(timeout=10)  # 超时可能抛出异常

# 修复后
try:
    self.downloader_process.wait(timeout=10)
except subprocess.TimeoutExpired:
    # 明确处理超时情况
    if self.downloader_process.poll() is None:
        self.downloader_process.terminate()
```

---

## 🧪 测试建议

### 测试场景1: 基本功能测试
```bash
# 1. 启动性能监控器
启动性能监控.bat

# 2. 启动智能恢复版（使用默认配置）
启动智能恢复版.bat
  - 直接按Enter使用默认值
  - 观察是否能正常启动

# 3. 在下载器中开始下载
# 4. 观察监控输出
```

### 测试场景2: 配置文件测试
```bash
# 1. 启动智能恢复版，输入自定义配置
启动智能恢复版.bat
  低速阈值: 300
  持续时间: 60
  自动开始: y

# 2. 检查生成的配置文件
type .era5_auto_recovery_config.json
# 应该看到：
# {
#   "low_speed_kb": 300,
#   "duration_sec": 60,
#   "auto_start": true
# }
```

### 测试场景3: 自动重启测试
```bash
# 1. 手动降低下载速度（可以限制带宽）
# 2. 观察是否能检测到低速
# 3. 观察30秒后是否自动重启
# 4. 重启后是否能正常继续下载
```

---

## 📋 修复文件清单

| 文件 | 修复内容 | 严重程度 |
|------|---------|---------|
| `ERA5_AutoRecovery.py` | 修复变量名错误 | ⚠️ 严重 |
| `ERA5_AutoRecovery.py` | 添加Windows API导入 | ⚠️ 严重 |
| `ERA5_AutoRecovery.py` | 改进窗口查找逻辑 | ℹ️ 轻微 |
| `ERA5_AutoRecovery.py` | 改进错误处理 | ℹ️ 轻微 |
| `启动智能恢复版.bat` | 修复JSON格式 | ⚠️ 中等 |

---

## 🎯 使用前检查清单

在运行智能恢复版之前，请确保：

- [ ] 已安装 pywin32：`uv pip install pywin32`
- [ ] 已启动性能监控器（或 era5_performance_monitor.py 在运行）
- [ ] era5_performance.db 数据库存在
- [ ] v3.0下载器（ERA5download_GUI_v3.py）存在
- [ ] 有足够的磁盘空间
- [ ] 网络连接正常

---

## 🚀 现在可以使用了！

修复完成后，智能自动恢复功能应该可以正常工作了。

### 快速启动
```bash
# 方式1：使用默认配置（推荐）
启动智能恢复版.bat
  (按3次Enter使用默认值)

# 方式2：自定义配置
启动智能恢复版.bat
  低速阈值: 300 KB/s
  持续时间: 60 秒
  自动开始: n
```

### 预期行为
1. ✅ 智能恢复版启动v3.0下载器
2. ✅ 每5秒检查下载速度
3. ✅ 速度低于阈值30秒后自动重启
4. ✅ 重启后利用断点续传无缝恢复
5. ✅ 无需任何手动干预

---

## 📝 技术要点

### 变量命名规范
- **用户输入变量**: 使用描述性后缀（如 `_kb`, `_sec`）
- **内部变量**: 使用完整单词（如 `threshold` 而非 `thresh`）
- **避免**: 缩写可能导致混淆

### 导入管理
```python
# 推荐：延迟导入 + 可用性检查
try:
    import module_name
    MODULE_AVAILABLE = True
except ImportError:
    MODULE_AVAILABLE = False

# 使用时检查
if MODULE_AVAILABLE:
    module_name.function()
```

### JSON生成
```batch
# 推荐：使用条件分支避免重复键
if "%VAR%"=="value" (
    echo   "key": true>> file.json
) else (
    echo   "key": false>> file.json
)
```

---

**修复完成！现在可以放心使用了！** ✅
