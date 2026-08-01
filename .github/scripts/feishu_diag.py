#!/usr/bin/env python3
"""诊断脚本：通过 User ID 获取 Feishu 用户信息"""

import os
import requests

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_ADMIN_OPEN_ID = os.environ.get("FEISHU_ADMIN_OPEN_ID", "")

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=data, timeout=15)
    result = resp.json()
    if result.get("code") == 0:
        print(f"  Token obtained: {result['tenant_access_token'][:20]}...")
        return result["tenant_access_token"]
    print(f"  Token error: {result}")
    return None

def get_user_info(user_id, token):
    """通过 user_id 获取用户信息"""
    url = f"https://open.feishu.cn/open-apis/contact/v3/users/{user_id}"
    params = {"user_id_type": "user_id", "department_id_type": "open_department_id"}
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers, params=params, timeout=15)
    result = resp.json()
    if result.get("code") == 0:
        user = result["data"]["user"]
        print(f"  User found:")
        print(f"    Name:       {user.get('name', 'N/A')}")
        print(f"    Open ID:    {user.get('open_id', 'N/A')}")
        print(f"    User ID:    {user.get('user_id', 'N/A')}")
        print(f"    Union ID:   {user.get('union_id', 'N/A')}")
        print(f"    Email:      {user.get('email', 'N/A')}")
        print(f"    Mobile:     {user.get('mobile', 'N/A')}")
        return user
    else:
        print(f"  Error: code={result.get('code')}, msg={result.get('msg')}")
        return None

def list_users(token):
    """列出应用可见的用户"""
    url = "https://open.feishu.cn/open-apis/contact/v3/users"
    params = {"page_size": 10, "user_id_type": "open_id"}
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers, params=params, timeout=15)
    result = resp.json()
    if result.get("code") == 0:
        users = result["data"].get("items", [])
        print(f"\n  ({len(users)} users visible to this app):")
        for u in users:
            print(f"    {u.get('name', '?')} - open_id: {u.get('open_id', 'N/A')}")
    else:
        print(f"  Error listing users: {result}")

print("=== Feishu User Diagnostic ===")
print(f"App ID:     {FEISHU_APP_ID}")
print(f"Admin ID:   {FEISHU_ADMIN_OPEN_ID}")

token = get_token()
if not token:
    print("FAILED: Cannot get token")
    exit(1)

print("\n[1] Lookup by User ID: 7655141557858815170")
user = get_user_info("7655141557858815170", token)

if not user:
    print("\n[2] Trying as open_id...")
    user = get_user_info(FEISHU_ADMIN_OPEN_ID, token)

if not user:
    print("\n[3] Listing all visible users...")
    list_users(token)
