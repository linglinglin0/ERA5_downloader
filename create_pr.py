#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""创建GitHub PR - 需要提供Token"""

import requests
import json
import os
import sys

# GitHub配置
REPO_OWNER = "linglinglin0"
REPO_NAME = "ERA5_downloader"
BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

def create_pr(token):
    """创建Pull Request"""

    # 读取PR描述
    pr_description_file = "PR_DESCRIPTION.md"
    if not os.path.exists(pr_description_file):
        print(f"[错误] 找不到PR描述文件: {pr_description_file}")
        return False

    with open(pr_description_file, 'r', encoding='utf-8') as f:
        pr_body = f.read()

    # GitHub API请求头
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }

    # PR数据
    pr_data = {
        "title": "fix: 修复连接泄漏导致的性能恶化问题",
        "body": pr_body,
        "head": "master",
        "base": "main"
    }

    print("[信息] 正在创建Pull Request...")

    try:
        response = requests.post(
            f"{BASE_URL}/pulls",
            headers=headers,
            data=json.dumps(pr_data),
            timeout=30
        )

        if response.status_code == 201:
            pr_info = response.json()
            print("=" * 80)
            print("✅ Pull Request 创建成功！")
            print("=" * 80)
            print(f"PR编号: #{pr_info['number']}")
            print(f"PR链接: {pr_info['html_url']}")
            return True
        elif response.status_code == 422:
            error_info = response.json()
            if "already exists" in str(error_info).lower():
                print("[信息] Pull Request已经存在")
                return True
            else:
                print(f"[错误] 创建失败: {error_info}")
                return False
        else:
            print(f"[错误] 状态码: {response.status_code}")
            return False

    except Exception as e:
        print(f"[错误] {e}")
        return False

def main():
    """主函数"""
    print("=" * 80)
    print(" " * 20 + "GitHub PR 创建工具")
    print("=" * 80)
    print()

    # 获取Token
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = input("请输入GitHub Token: ").strip()

    if not token:
        print("[错误] Token不能为空")
        print()
        print("获取Token: https://github.com/settings/tokens")
        return

    create_pr(token)

if __name__ == "__main__":
    main()
