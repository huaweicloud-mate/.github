#!/usr/bin/env python3
"""Probe GitCode git push - test main vs new branch, force vs non-force"""
import os, subprocess, sys, tempfile

TOKEN = os.environ.get("GITCODE_TOKEN", "")
REPO = "hd-vector/final-e2e-test"
url = f"https://oauth2:{TOKEN}@gitcode.com/{REPO}.git"

def run(args, cwd):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)
    return r

tmp = tempfile.mkdtemp(prefix="gitcode-push-")
subprocess.run(["git", "init", "-b", "main"], cwd=tmp, capture_output=True)
with open(os.path.join(tmp, "push-test.txt"), "w") as f:
    f.write("gitcode push test\n")
subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True)
subprocess.run(["git", "-c", "user.email=bot@test.dev", "-c", "user.name=test", "commit", "-m", "test"], cwd=tmp, capture_output=True)

# 1. push new branch
print("[TEST 1] push new branch 'test-branch'")
r = run(["git", "push", url, "main:test-branch"], tmp)
print("  ", "OK" if r.returncode == 0 else "FAIL", r.stderr.strip().split("\n")[0][:150] if r.stderr else "")
if r.returncode == 0:
    run(["git", "push", url, "--delete", "test-branch"], tmp)

# 2. push main (non-force)
print("[TEST 2] push main (non-force)")
r = run(["git", "push", url, "main:main"], tmp)
print("  ", "OK" if r.returncode == 0 else "FAIL", r.stderr.strip().split("\n")[0][:150] if r.stderr else "")

# 3. push main (force)
print("[TEST 3] push main (force)")
r = run(["git", "push", "--force", url, "main:main"], tmp)
print("  ", "OK" if r.returncode == 0 else "FAIL", r.stderr.strip().split("\n")[0][:150] if r.stderr else "")

print("=== probe done ===")
