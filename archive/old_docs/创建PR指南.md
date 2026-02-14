# 🚀 通过命令行自动创建PR

## 方法一：使用Python脚本（推荐）⭐

### 步骤1：获取GitHub Token

1. 访问：https://github.com/settings/tokens
2. 点击 **"Generate new token (classic)"**
3. 勾选权限：
   - ✅ **repo** (完整权限)
4. 点击 **"Generate token"**
5. **复制token**（只显示一次，请妥善保管）

### 步骤2：设置环境变量并创建PR

在命令行运行：

```batch
cd D:\wzl\ERA5下载软件
set GITHUB_TOKEN=你的token
C:\Users\Administrator\.local\bin\uv.exe run python create_pr.py
```

### 示例

```batch
set GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
uv run python create_pr.py
```

---

## 方法二：使用Curl（无需Python）

```batch
cd D:\wzl\ERA5下载软件
set GITHUB_TOKEN=你的token

curl -X POST https://api.github.com/repos/linglinglin0/ERA5_downloader/pulls ^
  -H "Authorization: token %GITHUB_TOKEN%" ^
  -H "Accept: application/vnd.github.v3+json" ^
  -H "Content-Type: application/json" ^
  -d @pr_data.json
```

其中 `pr_data.json` 包含PR信息。

---

## 方法三：直接在浏览器创建（最简单）

1. 访问：https://github.com/linglinglin0/ERA5_downloader
2. 点击 **"Pull requests"** → **"New pull request"**
3. 填写标题和描述（见下方）

### PR标题
```
fix: 修复连接泄漏导致的性能恶化问题
```

### PR描述
复制 `PR_DESCRIPTION.md` 的内容

---

## 📝 快速创建（推荐）

### 使用Python脚本

```batch
cd D:\wzl\ERA5下载软件

# 1. 设置token（替换为你的实际token）
set GITHUB_TOKEN=ghp_你的token

# 2. 运行脚本
C:\Users\Administrator\.local\bin\uv.exe run python create_pr.py
```

脚本会自动：
- ✅ 读取PR描述文件
- ✅ 调用GitHub API
- ✅ 创建Pull Request
- ✅ 显示PR链接

---

## 🎯 现在开始

**请选择一种方式：**

**A. 使用Python脚本（自动）** - 需要GitHub Token
**B. 使用浏览器手动创建** - 无需Token

如果选择方式A，请先获取GitHub Token，然后告诉我，我帮您运行脚本。

如果选择方式B，请访问：
```
https://github.com/linglinglin0/ERA5_downloader
```

点击 "Pull requests" → "New pull request"

---

**您想用哪种方式？**
