#!/usr/bin/env python3
"""Probe GitCode v5 API - proper api.gitcode.com domain"""
import json, os
import urllib.request, urllib.error

TOKEN = os.environ.get("GITCODE_TOKEN", "")
ORG = os.environ.get("GITCODE_ORG", "hd-vector")
BASES = ["https://api.gitcode.com/api/v5", "https://gitcode.com/api/v5"]
HEADERS = {"PRIVATE-TOKEN": TOKEN, "Content-Type": "application/json", "User-Agent": "gitcode-probe"}


def probe(base, method, path, data=None):
    url = f"{base}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode()[:400]
            print(f"[OK]   {base}{path} -> {resp.status}: {raw[:300]}")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:200]
        print(f"[ERR]  {base}{path} -> {e.code}: {raw}")
        return e.code, raw
    except Exception as e:
        print(f"[FAIL] {base}{path} -> {e}")
        return None, None


print(f"=== GitCode v5 probe v2 (org={ORG}) ===")

for base in BASES:
    print(f"\n--- Base: {base} ---")
    # user - confirm works on this base
    probe(base, "GET", "/user")

    # projects under user
    probe(base, "GET", "/user/projects")
    probe(base, "GET", f"/users/{ORG}/projects")

    # groups
    probe(base, "GET", f"/user/groups")
    probe(base, "GET", f"/users/{ORG}")

    # org-style
    probe(base, "GET", f"/orgs/{ORG}")

    # repo path style
    probe(base, "GET", f"/repos/{ORG}")
    probe(base, "GET", f"/repositories")

print("\n=== probe v2 complete ===")
