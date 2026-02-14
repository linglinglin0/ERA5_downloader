#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交互式创建GitHub Pull Request
"""

import requests
import json
import os

# GitHub配置
REPO_OWNER = "linglinglin0"
REPO_NAME = "ERA5_downloader"
BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

def create_pr_with_token(token):
    """使用给定token创建PR"""

    # 读取PR描述
    pr_description_file = "PR_DESCRIPTION.md"
    if not os.path.exists(pr_description_file):
        print(f"[错误] 找不到PR描述文件: {pr_description_file}")
        return None

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
        "head": "main",
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
            return {
                'success': True,
                'number': pr_info['number'],
                'title': pr_info['title'],
                'url': pr_info['html_url'],
                'state': pr_info['state']
            }
        elif response.status_code == 422:
            error_info = response.json()
            if "pull request already exists" in str(error_info).lower():
                return {
                    'success': True,
                    'exists': True,
                    'message': 'Pull Request已经存在'
                }
            else:
                return {
                    'success': False,
                    'error': error_info
                }
        else:
            return {
                'success': False,
                'status_code': response.status_code,
                'message': response.text
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def main():
    """主函数"""
    print("=" * 80)
    print(" " * 15 + "GitHub PR 自动创建工具")
    print("=" * 80)
    print()

    # 检查PR描述文件
    if not os.path.exists("PR_DESCRIPTION.md"):
        print("[错误] 找不到PR_DESCRIPTION.md文件")
        print("[提示] 请确保在项目目录下运行此脚本")
        return

    # 获取Token
    print("[提示] 需要GitHub Personal Access Token才能创建PR")
    print()
    print("获取Token的步骤:")
    print("1. 访问: https://github.com/settings/tokens")
    print("2. 点击 'Generate new token (classic)'")
    print("3. 勾选 'repo' 权限")
    print("4. 生成Token并复制")
    print()

    token = input("请输入您的GitHub Token: ").strip()

    if not token:
        print("[错误] Token不能为空")
        return

    print()
    print("[信息] 正在连接GitHub...")

    # 创建PR
    result = create_pr_with_token(token)

    print()
    print("=" * 80)

    if result and result.get('success'):
        if result.get('exists'):
            print("[信息] Pull Request已经存在")
        else:
            print("✅ Pull Request 创建成功！")
            print()
            print(f"PR编号: #{result['number']}")
            print(f"PR标题: {result['title']}")
            print(f"PR链接: {result['url']}")
            print()
            print(f"您可以点击以下链接查看PR:")
            print(result['url'])
    else:
        print("[错误] 创建PR失败")
        if result:
            if result.get('status_code'):
                print(f"状态码: {result['status_code']}")
            if result.get('message'):
                print(f"错误信息: {result['message']}")
            if result.get('error'):
                print(f"错误详情: {result['error']}")

    print("=" * 80)

if __name__ == "__main__":
    main()
