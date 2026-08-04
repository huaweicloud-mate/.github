#!/usr/bin/env python3
"""Clean up probe test repos on GitCode"""
import json, os
import urllib.request, urllib.error

TOKEN = os.environ.get("GITCODE_TOKEN", "")
BASE = "https://api.gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": TOKEN, "Content-Type": "application/json", "User-Agent": "gitcode-cleanup"}


def req(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            raw = resp.read().decode()[:200]
            print(f"[OK]   {method} {path} -> {resp.status}: {raw[:120]}")
    except urllib.error.HTTPError as e:
        print(f"[ERR]  {method} {path} -> {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"[FAIL] {method} {path} -> {e}")


# Try delete endpoints for both probe repos
req("DELETE", "/repos/hd-vector/__probe_invalid_name__")
req("DELETE", "/repos/shuangzhangj/__probe_invalid_name__")
