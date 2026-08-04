#!/usr/bin/env python3
"""Probe GitCode git auth URL formats"""
import os, subprocess, sys

TOKEN = os.environ.get("GITCODE_TOKEN", "")
USER = os.environ.get("GITCODE_USERNAME", "")
REPO = "hd-vector/final-e2e-test"

formats = [
    ("oauth2-token", f"https://oauth2:{TOKEN}@gitcode.com/{REPO}.git"),
    ("user-token", f"https://{USER}:{TOKEN}@gitcode.com/{REPO}.git"),
    ("token-only", f"https://{TOKEN}@gitcode.com/{REPO}.git"),
    ("oauth2-user", f"https://oauth2:{USER}:{TOKEN}@gitcode.com/{REPO}.git"),
    ("user-oauth2token", f"https://{USER}:oauth2:{TOKEN}@gitcode.com/{REPO}.git"),
]

for name, url in formats:
    # mask token in output
    masked = url.replace(TOKEN, "***") if TOKEN else url
    r = subprocess.run(
        ["git", "ls-remote", url, "HEAD"],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode == 0:
        print(f"[OK]   {name}: {masked}")
        print("  -> SUCCESS: this format works!")
        sys.exit(0)
    else:
        # get error message
        err = r.stderr.strip().split("\n")
        key = next((l for l in err if "fatal" in l or "Authentication" in l or "denied" in l or "removed" in l), r.stderr.strip()[:120])
        print(f"[FAIL] {name}: {masked}")
        print(f"  -> {key[:150]}")
