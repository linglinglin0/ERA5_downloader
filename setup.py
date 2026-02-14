"""
ERA5 数据下载工具 - 安装配置
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="era5-downloader",
    version="3.1.0",
    author="ERA5 Downloader Team",
    author_email="your-email@example.com",
    description="一个高性能的 ERA5 气象数据下载工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/ERA5-downloader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "customtkinter>=5.0.0",
        "boto3>=1.28.0",
        "botocore>=1.31.0",
        "netCDF4>=1.6.0",
        "psutil>=5.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-qt>=4.0.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "pylint>=2.17.0",
            "mypy>=1.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "era5-downloader=era5.gui:main",
        ],
    },
)
