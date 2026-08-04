#!/usr/bin/env python3
"""Probe GitCode git push auth - test actual write permission"""
import os, subprocess, sys, tempfile

TOKEN = os.environ.get("GITCODE_TOKEN", "")
REPO = "hd-vector/final-e2e-test"

url = f"https://oauth2:{TOKEN}@gitcode.com/{REPO}.git"

# create temp repo with a commit
tmp = tempfile.mkdtemp(prefix="gitcode-push-")
subprocess.run(["git", "init", "-b", "main"], cwd=tmp, capture_output=True)
with open(os.path.join(tmp, "push-test.txt"), "w") as f:
    f.write("gitcode push auth test\n")
subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True)
subprocess.run(["git", "-c", "user.email=bot@test.dev", "-c", "user.name=test", "commit", "-m", "push auth test"], cwd=tmp, capture_output=True)

# try push to a test branch
r = subprocess.run(["git", "push", url, "main:auth-test-branch"], cwd=tmp, capture_output=True, text=True, timeout=60)
if r.returncode == 0:
    print("[OK]   PUSH SUCCESS - token has write access")
    # cleanup test branch
    subprocess.run(["git", "push", url, "--delete", "auth-test-branch"], cwd=tmp, capture_output=True, timeout=60)
    print("[OK]   test branch deleted")
    sys.exit(0)
else:
    print("[FAIL] PUSH FAILED")
    for line in r.stderr.split("\n"):
        if line.strip() and ("fatal" in line.lower() or "denied" in line.lower() or "error" in line.lower() or "permission" in line.lower() or "removed" in line.lower() or "remote" in line.lower()):
            print(f"  -> {line.strip()[:200]}")
    sys.exit(1)
