#!/usr/bin/env python3
"""Probe GitCode v5 API endpoints to find correct paths"""
import json, os, sys
import urllib.request, urllib.error

TOKEN = os.environ.get("GITCODE_TOKEN", "")
ORG = os.environ.get("GITCODE_ORG", "hd-vector")
BASE = "https://gitcode.com/api/v5"

HEADERS = {"PRIVATE-TOKEN": TOKEN, "Content-Type": "application/json", "User-Agent": "gitcode-probe"}


def probe(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()[:800]
            print(f"[OK]   {method} {path} -> {resp.status}: {raw[:500]}")
            return resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:300]
        print(f"[ERR]  {method} {path} -> {e.code}: {raw}")
        return e.code
    except Exception as e:
        print(f"[FAIL] {method} {path} -> {e}")
        return None


print(f"=== GitCode v5 API probe (org={ORG}) ===")
print(f"Base: {BASE}")

# 1. user endpoints - verify token works
probe("GET", "/user")
probe("GET", "/users/me")
probe("GET", "/users")

# 2. namespace / groups endpoints
probe("GET", "/groups")
probe("GET", f"/groups/{ORG}")
probe("GET", f"/namespaces")
probe("GET", f"/namespaces?search={ORG}")

# 3. projects endpoints
probe("GET", "/projects")
probe("GET", "/projects?owned=true")
probe("GET", "/user/projects")
probe("GET", f"/projects?search={ORG}")

# 4. try different base patterns
probe("GET", f"/orgs/{ORG}/projects")
probe("GET", f"/groups/{ORG}/projects")

print("=== probe complete ===")
