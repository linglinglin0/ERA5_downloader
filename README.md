# ERA5 数据下载工具

> 一个基于 Python 和 CustomTkinter 的图形化 ERA5 气象数据批量下载客户端，支持断点续传、多线程并发下载和实时进度监控。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v2.1-orange.svg)](CHANGELOG.md)

---

## 📋 项目简介

ERA5 数据下载工具是一个现代化的桌面应用程序，旨在简化从 NCAR AWS S3 存储桶批量下载 ERA5 再分析数据的过程。通过直观的图形界面，用户可以轻松配置下载参数，监控实时进度，并在网络中断后自动恢复下载。

### 核心特性

- 🎯 **变量筛选** - 支持按类别选择动力/热力学、湿度/云物理、化学成分等变量
- ⚡ **多线程下载** - 可配置 1-10 个并发线程，支持速度监控
- 🔄 **智能续传** - 自动检测本地文件完整性，支持断点续传
- 💾 **配置记忆** - 自动保存下载设置（日期、路径、变量选择）
- 📊 **实时监控** - 显示每线程下载进度、速度统计和系统日志
- ⚠️ **错误处理** - 网络错误自动重试，详细错误日志记录

---

## 🚀 快速开始

### 环境要求

- **Python 版本**: 3.8 或更高
- **操作系统**: Windows / Linux / macOS
- **网络连接**: 需要能够访问 AWS S3 服务
- **磁盘空间**: 根据下载数据量准备足够空间（通常每月数据约 10-50 GB）

### 安装依赖

```bash
# 使用 requirements.txt 安装所有依赖
pip install -r requirements.txt

# 或者手动安装核心依赖
pip install customtkinter boto3
```

### 启动应用

```bash
python era5/gui.py
```

或在 Windows 上直接双击 `era5/gui.py` 文件使用 Python Launcher 打开。

---

## 📖 使用指南

### 基本操作流程

1. **设置日期**
   - 在"年月"输入框中输入目标日期（格式：`YYYYMM`，例如 `202510`）

2. **选择目录**
   - 点击"选择文件夹"按钮设置数据保存根目录
   - 建议使用专门的文件夹，如 `D:\ERA5数据\`

3. **选择变量**（可选）
   - 勾选需要下载的 ERA5 变量
   - 不勾选任何变量时，默认下载全部变量

4. **配置线程**
   - 拖动滑块设置并发下载线程数（1-10，推荐 5）

5. **开始下载**
   - 点击"开始下载"按钮
   - 监控实时进度和速度

### 可用变量

| 类别 | 变量代码 | 描述 | 单位 |
|------|---------|------|------|
| 温度 | `t` | 空气温度 | K |
| 风 | `u`, `v` | U/V 风分量 | m/s |
| 湿度 | `q` | 比湿 | kg/kg |
| 湿度 | `r` | 相对湿度 | % |
| 云 | `cc` | 云量 | 0-1 |
| 垂直运动 | `w` | 垂直速度 | Pa/s |
| 位势 | `z` | 位势高度 | m²/s² |
| 涡度 | `d` | 散度 | - |
| 涡度 | `vo` | 相对涡度 | s⁻¹ |
| 涡度 | `pv` | 位涡 | PVU |
| 云水 | `ciwc` | 云冰含量 | kg/kg |
| 云水 | `clwc` | 云液水含量 | kg/kg |
| 降水 | `crwc` | 雨水含量 | kg/kg |
| 降水 | `cswc` | 雪水含量 | kg/kg |
| 化学 | `o3` | 臭氧 | kg/kg |

---

## ✨ 新功能亮点 (v2.1)

### 1. 断点续传

不用担心网络中断！程序会自动：
- **网络错误自动重试**：失败后自动重试 3 次
- **保留下载进度**：临时文件（`.tmp`）会被保留
- **智能续传**：重新启动时自动从断点继续

### 2. 配置自动记忆

程序会自动保存你的设置：
- ✅ 日期
- ✅ 保存目录路径
- ✅ 并发线程数
- ✅ 勾选的变量列表

下次打开时无需重新设置！

### 3. 实时百分比显示

下载时显示详细的文字百分比进度：
- `50%` - 下载进度
- `50% (重试1)` - 重试中
- `断点续传 60.5MB` - 从断点恢复
- `已存在(跳过)` - 文件已完整

---

## 📂 项目结构

```
era5-download-tool/
├── era5/                          # 主应用模块
│   ├── __init__.py
│   └── gui.py                      # 主应用程序（GUI + 下载逻辑）
│
├── docs/                           # 项目文档
│   ├── user/                        # 用户文档
│   │   ├── 快速开始.md              # 快速入门指南
│   │   ├── 新功能使用说明.md        # v2.1 功能详解
│   │   ├── 断点续传使用指南.md    # 断点续传教程
│   │   └── API文档.md              # API 接口说明
│   │
│   ├── dev/                         # 开发文档
│   │   ├── 断点续传功能说明.md    # 技术实现文档
│   │   ├── 性能问题分析与改进方案.md
│   │   ├── 性能改进实施总结.md
│   │   ├── Bug修复总结.md
│   │   ├── 打包和分发指南.md
│   │   └── ...
│   │
│   └── reports/                     # 项目报告
│       ├── 文件打包清单.md
│       └── 下载不完整问题分析报告.md
│
├── scripts/                        # 辅助脚本
│   ├── diagnostic_tool.py            # 诊断工具
│   ├── log_analyzer.py              # 日志分析器
│   ├── 网络诊断工具.py
│   └── 生成监控报告.py
│
├── archive/                        # 归档目录
│   ├── old_versions/                # 历版本备份
│   ├── old_docs/                    # 历文档归档
│   └── dev_scripts/                 # 开发脚本存档
│
├── .spec-workflow/                 # 工作流模板
│   └── templates/                   # 规格文档模板
│
├── requirements.txt                 # 生产环境依赖
├── requirements-dev.txt             # 开发环境依赖
├── CLAUDE.md                      # 项目架构文档
└── README.md                       # 本文件
```

---

## 🔧 高级功能

### 批量下载多月数据

1. 第一次运行：
   - 日期：`202410`
   - 目录：`D:\ERA5数据\2024年第4季度\`
   - 其他配置按需设置
2. 第二次运行：
   - 修改日期为：`202411`
   - 其他设置保持不变
3. 重复步骤下载其他月份

### 性能优化建议

- **网络稳定时**：使用 8-10 个线程
- **网络不稳定时**：使用 3-5 个线程
- **避免高峰期**：在网络使用较少时段下载
- **有线连接**：使用有线网络比 WiFi 更稳定

### 错误处理

如果下载遇到问题：
1. 查看 `download_errors.log` 获取详细错误信息
2. 使用 `scripts/diagnostic_tool.py` 进行网络诊断
3. 使用 `scripts/log_analyzer.py` 分析下载日志

---

## ⚠️ 常见问题

### Q1: 下载速度很慢？

**解决方法**：
- 增加线程数到 8-10
- 检查网络带宽
- 避开网络高峰时段
- 确保没有其他程序占用带宽

### Q2: 提示"网络错误"？

**处理方法**：
- 程序会自动重试 3 次
- 检查网络连接
- 如果持续失败，尝试减少线程数
- 查看错误日志获取详细信息

### Q3: 磁盘空间不足？

**预防措施**：
- 每月数据约 10-50 GB
- 分批下载不同月份
- 定期清理不需要的数据

### Q4: 如何知道下载完成了？

**确认方法**：
- 进度区域显示"完成"
- 日志区域显示"所有文件已下载完成"
- 目标文件夹中有 `.nc` 文件（无 `.tmp` 后缀）

---

## 🛠️ 开发指南

### 技术栈

- **GUI 框架**: CustomTkinter (现代化 Tkinter 主题)
- **网络传输**: Boto3 (AWS SDK for Python) + S3 协议
- **并发模型**: ThreadPoolExecutor (线程池)
- **数据源**: NSF-NCAR ERA5 公开 S3 存储桶 (`nsf-ncar-era5`)

### 架构模式

- **MVC 变体**: 单文件集成 Model（数据逻辑）、View（GUI 组件）、Controller（事件处理）
- **异步设计**: 下载任务在独立线程运行，通过 `after()` 回调更新 UI
- **生产者-消费者**: 使用队列管理线程槽位，确保资源可控

### 代码规范

- **命名约定**:
  - 类名: 大驼峰 (`ERA5ResumeDownloadApp`)
  - 方法/函数: 蛇形 (`get_selected_vars`)
  - 常量: 全大写蛇形 (`ERA5_VARS`)

- **最佳实践**:
  1. 线程安全：使用 `threading.Lock()` 保护共享变量
  2. 资源清理：停止下载时强制清理临时文件并关闭网络连接
  3. 错误处理：下载失败不中断整体任务，记录状态到 UI
  4. UI 响应：长时间任务使用独立线程，通过 `after()` 更新 UI

### 添加新变量

编辑 `era5/gui.py` 中的 `ERA5_VARS` 字典：

```python
ERA5_VARS = {
    "动力与热力学": {
        "t": "空气温度 (K)",
        "u": "U风分量 (m/s)",
        # 添加新变量
        "new_var": "新变量描述"
    }
}
```

---

## 📊 性能特性

- **并发下载**: 支持 1-10 个线程同时下载
- **断点续传**: 使用 HTTP Range 请求实现分块续传
- **智能重试**: 指数退避算法，最多重试 6 次
- **进度持久化**: JSON 文件记录已完成文件列表
- **速度监控**: 实时显示下载速度（MB/s）

---

## 📝 更新日志

### v2.1 (2026-01-19)

**新增功能**:
- ✅ 实时百分比显示
- ✅ 配置自动记忆
- ✅ 断点续传支持
- ✅ 自动重试机制
- ✅ 进度状态持久化

**改进优化**:
- 🎨 优化 UI 更新频率
- 🚀 提升下载速度
- 🐛 修复多个已知问题

完整更新日志请查看 [CHANGELOG.md](CHANGELOG.md)

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🔗 相关资源

- **ERA5 官方文档**: https://www.ecmwf.int/en/forecasts/datasets/reanalysis-datasets/era5
- **NCAR AWS S3 访问**: https://data.nccs.nasa.gov/thornes/ERA5/
- **CustomTkinter 文档**: https://customtkinter.tomschimansky.com/
- **Boto3 S3 客户端**: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html

---

## 💬 联系方式

如有问题或建议，请：
- 提交 Issue
- 查看项目文档
- 阅读使用指南

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

Made with ❤️ by ERA5 Data Download Tool Team

</div>
