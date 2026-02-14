# 根目录完整清理方案

## 当前状态

根目录还有 **约35个旧文件**需要清理：

### 旧版本程序（3个）
- `ERA5download_GUI_v2.py`
- `ERA5download_GUI_v2_fixed.py`
- `era5_advanced_features.py`

### 旧文档（10+个）
- `CLAUDE.md`
- `CODE_REVIEW_REPORT.md`
- `GIT提交计划.md`
- `PR_DESCRIPTION.md`
- `PULL_REQUEST.md`
- `README_总览.md`
- `UV使用指南.md`
- `setup_env.bat`
- `setup_env_uv.bat`

### 重复脚本（5个）
- `create_pr.py`
- `create_pr_interactive.py`
- `diagnostic_tool.py`
- `log_analyzer.py`
- `网络诊断工具.py`
- `生成监控报告.py`

### 其他文件（5个）
- `main.py`
- `src/` (旧源代码目录)
- `生成监控报告.py`
- `pyproject.toml`
- `uv.lock`

## 清理计划

### 第1步：移动旧版本
```bash
mv ERA5download_GUI_v2.py ERA5download_GUI_v2_fixed.py era5_advanced_features.py archive/old_versions/
```

### 第2步：移动旧文档
```bash
mv CLAUDE.md CODE_REVIEW_REPORT.md GIT提交计划.md \
   PR_DESCRIPTION.md PULL_REQUEST.md README_总览.md \
   UV使用指南.md archive/old_docs/
```

### 第3步：删除重复脚本（已存在于scripts/）
```bash
rm -f create_pr.py create_pr_interactive.py diagnostic_tool.py \
        log_analyzer.py 网络诊断工具.py 生成监控报告.py
```

### 第4步：删除其他旧文件
```bash
rm -f main.py pyproject.toml uv.lock
rm -rf src/
```

## 最终结果

清理后根目录应该只有：
- `.git/`, `.gitignore`, `.claude/`, `.spec-workflow/`
- `archive/`（归档）
- `docs/`（核心文档）
- `era5/`（主程序）
- `scripts/`（工具脚本）
- `tests/`（测试）
- `LICENSE`, `README.md`, `requirements.txt`, `requirements-dev.txt`, `setup.py`

**总计：19个核心文件/目录**
