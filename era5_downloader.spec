# -*- mode: python ; coding: utf-8 -*-
"""
ERA5 数据下载工具 - PyInstaller 打包配置

使用方法:
  pyinstaller era5_downloader.spec

生成文件位置:
  dist/era5_downloader/
"""

block_cipher = False
block_cipher = False

# 基础配置
a = Analysis(
    ['era5/gui.py'],              # 主程序入口
    pathex=['.', 'era5'],          # Python 模块搜索路径
    binaries=[],
    datas=[
        # 包含 README 文档
        ('README.md', '.'),

        # 可选：包含文档文件
        # ('docs', 'docs'),
    ],
    hiddenimports=[
        'boto3',
        'botocore',
        'customtkinter',
        'tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'pytest',
        'pandas',
        'numpy',
        'scipy',
    ],
    win_no_prefer_redirect=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 文件夹分发配置（推荐）
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ERA5数据下载工具',           # 可执行文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                          # 启用 UPX 压缩（减小体积）
    console_runtime_hooks=[],
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                          # 可以添加 .ico 图标文件
    console=False,                      # GUI 程序，不显示控制台窗口
    disable_logger=None,
)

# 收集所有依赖
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,                          # 启用 UPX 压缩
    upx_exclude=[],
    name='era5_downloader',            # 输出文件夹名称
)
