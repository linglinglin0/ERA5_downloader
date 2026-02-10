#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""删除GitHub Release - 谨慎使用"""

import requests
import sys

# GitHub配置
REPO_OWNER = "linglinglin0"
REPO_NAME = "ERA5_downloader"
BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

def delete_release(token, tag_name):
    """删除指定版本的Release"""

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 先获取release ID
    response = requests.get(f"{BASE_URL}/releases/tags/{tag_name}", headers=headers)

    if response.status_code != 200:
        print(f"[错误] 找不到Release {tag_name}: {response.text}")
        return False

    release_info = response.json()
    release_id = release_info['id']

    print(f"[信息] 找到Release: {release_info['name']}")
    print(f"[信息] Release ID: {release_id}")
    print()

    # 二次确认
    confirm = input(f"确认删除Release {tag_name}? (输入 YES 确认): ")
    if confirm != "YES":
        print("[取消] 操作已取消")
        return False

    # 删除release
    response = requests.delete(f"{BASE_URL}/releases/{release_id}", headers=headers)

    if response.status_code == 204:
        print(f"[成功] Release {tag_name} 已删除")

        # 同时删除标签
        response = requests.delete(f"{BASE_URL}/git/refs/tags/{tag_name}", headers=headers)
        if response.status_code == 204:
            print(f"[成功] 标签 {tag_name} 已删除")
        else:
            print(f"[警告] 删除标签失败: {response.text}")

        return True
    else:
        print(f"[错误] 删除失败: {response.text}")
        return False

def main():
    """主函数"""
    print("=" * 80)
    print(" " * 25 + "删除GitHub Release")
    print("=" * 80)
    print()

    # 获取参数
    if len(sys.argv) < 3:
        print("用法: python delete_release.py <token> <tag_name>")
        print("示例: python delete_release.py ghp_xxx v1.0.0")
        return

    token = sys.argv[1]
    tag_name = sys.argv[2]

    delete_release(token, tag_name)

if __name__ == "__main__":
    main()
