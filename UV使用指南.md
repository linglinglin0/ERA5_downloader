# UV 包管理器 - 使用指南

## ✅ UV 安装成功！

**安装位置：** `C:\Users\Administrator\.local\bin`
**当前版本：** uv 0.10.0

---

## 🔧 永久添加到 PATH（推荐）

### 方法一：使用 PowerShell（自动）

以**管理员身份**运行 PowerShell，执行：

```powershell
[Environment]::SetEnvironmentVariable("Path", "C:\Users\Administrator\.local\bin;" + [Environment]::GetEnvironmentVariable("Path", "User"), "User")
```

### 方法二：手动添加

1. 右键点击 `此电脑` → `属性`
2. 点击 `高级系统设置` → `环境变量`
3. 在 `用户变量` 中找到 `Path`
4. 点击 `编辑` → `新建`
5. 添加：`C:\Users\Administrator\.local\bin`
6. 点击 `确定` 保存

**重启终端使PATH生效**

---

## 🚀 使用 UV 配置 ERA5 项目

我已经为您创建了使用 uv 的配置脚本：

### 快速配置（推荐）

```batch
# 进入项目目录
cd D:\wzl\ERA5下载软件

# 运行配置脚本
setup_env_uv.bat
```

这个脚本会自动：
- ✅ 初始化 uv 项目
- ✅ 安装所有依赖包
- ✅ 创建 `uv.lock` 锁文件

### 启动程序

```batch
# 方式1：使用快捷脚本
启动程序_uv.bat

# 方式2：手动执行
cd D:\wzl\ERA5下载软件
uv run python ERA5download_GUI_v2.py
```

---

## 📦 UV 常用命令

### 项目管理

```bash
# 初始化新项目
uv init

# 添加依赖包
uv add package-name

# 添加开发依赖
uv add --dev pytest

# 移除依赖包
uv remove package-name

# 更新所有依赖
uv sync

# 查看依赖树
uv tree
```

### Python 版本管理

```bash
# 查找可用的Python版本
uv python list

# 安装特定Python版本
uv python install 3.11

# 设置项目Python版本
uv python pin 3.11
```

### 虚拟环境

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### 运行和构建

```bash
# 运行Python脚本
uv run python script.py

# 运行测试
uv run pytest

# 构建包
uv build
```

---

## ⚡ UV vs Pip 对比

| 特性 | UV | Pip |
|------|-----|-----|
| **速度** | ⚡ 极快（100x） | 🐌 较慢 |
| **依赖解析** | 🔍 并行快速 | 📝 串行较慢 |
| **锁文件** | ✅ uv.lock | ❌ 无 |
| **Python版本管理** | ✅ 内置 | ❌ 需要pyenv |
| **包管理** | ✅ 统一工具 | ⚠️ 分散工具 |
| **兼容性** | ✅ 兼容pip | ✅ 标准工具 |

---

## 🎯 ERA5 项目使用 UV 的优势

### 1. 极快的安装速度
```
传统 pip 安装: ~30-60秒
UV 安装:       ~2-5秒
```

### 2. 可重现的构建
- `uv.lock` 确保每次安装相同的版本
- 团队协作更可靠

### 3. 统一工具链
- 包管理、Python版本管理、虚拟环境一体化
- 无需安装多个工具

---

## 📁 项目结构（使用UV后）

```
ERA5下载软件/
├── ERA5download_GUI_v2.py    # 主程序
├── requirements.txt           # pip依赖清单（备用）
├── pyproject.toml             # UV项目配置（自动生成）
├── uv.lock                    # UV依赖锁文件（自动生成）
├── .venv/                     # UV虚拟环境（自动生成）
├── setup_env_uv.bat           # UV环境配置脚本
├── 启动程序_uv.bat             # UV启动脚本
├── setup_env.bat              # pip环境配置脚本（备用）
└── 启动程序.bat                # pip启动脚本（备用）
```

---

## 🔍 配置文件说明

### pyproject.toml（UV项目配置）
```toml
[project]
name = "era5-download"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "customtkinter>=5.0.0",
    "boto3>=1.28.0",
    "botocore>=1.31.0",
]
```

### uv.lock（依赖锁文件）
- 自动生成，精确记录每个依赖的版本
- 确保团队使用相同版本
- **不要手动编辑**

---

## 💡 使用建议

### 推荐工作流

1. **首次配置**
   ```bash
   setup_env_uv.bat  # 一键配置
   ```

2. **日常使用**
   ```bash
   启动程序_uv.bat   # 启动程序
   ```

3. **添加新依赖**
   ```bash
   uv add new-package  # 自动更新pyproject.toml和uv.lock
   ```

4. **团队协作**
   ```bash
   git clone repo
   cd project
   uv sync  # 一键安装所有依赖（使用uv.lock）
   ```

---

## ❓ 常见问题

### Q1: uv 命令找不到？
**A:** 需要将 `C:\Users\Administrator\.local\bin` 添加到 PATH 环境变量（见上方说明）

### Q2: 如何切换回使用 pip？
**A:** 直接运行 `setup_env.bat` 和 `启动程序.bat`

### Q3: uv 和 pip 可以混用吗？
**A:** 不建议。选择一种作为主要工具，推荐使用 uv（更快更可靠）

### Q4: 如何更新 uv？
```bash
uv self update
```

### Q5: uv 安装失败怎么办？
```bash
# 使用国内镜像
export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 🌟 下一步

1. **添加 UV 到 PATH**（可选但推荐）
2. **运行配置脚本**：`setup_env_uv.bat`
3. **启动程序**：`启动程序_uv.bat`

享受极快的包管理体验！⚡
