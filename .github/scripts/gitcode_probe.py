#!/usr/bin/env python3
"""Probe GitCode v5 - org repos + create repo endpoints"""
import json, os
import urllib.request, urllib.error

TOKEN = os.environ.get("GITCODE_TOKEN", "")
ORG = os.environ.get("GITCODE_ORG", "hd-vector")
BASE = "https://api.gitcode.com/api/v5"
HEADERS = {"PRIVATE-TOKEN": TOKEN, "Content-Type": "application/json", "User-Agent": "gitcode-probe"}


def probe(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()[:400]
            print(f"[OK]   {method} {path} -> {resp.status}: {raw[:300]}")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:250]
        print(f"[ERR]  {method} {path} -> {e.code}: {raw}")
        return e.code, raw
    except Exception as e:
        print(f"[FAIL] {method} {path} -> {e}")
        return None, None


print(f"=== GitCode v5 org repos + create probe (org={ORG}, id=14018284) ===")

# list org repos
probe("GET", f"/orgs/{ORG}/repos")
probe("GET", f"/orgs/{ORG}/repositories")
probe("GET", f"/orgs/14018284/repos")

# list user's repos
probe("GET", "/user/repos")
probe("GET", "/repos")

# create repo - try various endpoints (DRY RUN: use invalid name to see routing)
test_name = "__probe_invalid_name__"
create_body = {"name": test_name, "description": "probe", "private": False}
probe("POST", "/orgs/hd-vector/repos", create_body)
probe("POST", "/orgs/14018284/repos", create_body)
probe("POST", "/user/repos", create_body)
probe("POST", "/repos", create_body)
probe("POST", f"/users/{ORG}/repos", create_body)

print("\n=== probe v3 complete ===")
