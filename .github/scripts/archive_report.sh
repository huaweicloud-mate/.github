#!/bin/bash
# 归档报告到 huaweicloud-mate/reports 仓库
set -e

REPORT_FILE="$1"
ARCHIVE_PATH="$2"
COMMIT_MSG="$3"

if [ ! -f "$REPORT_FILE" ]; then
    echo "Report file not found: $REPORT_FILE"
    exit 1
fi

REPO_URL="https://x-access-token:${ARCHIVE_TOKEN}@github.com/huaweicloud-mate/reports.git"
ARCHIVE_DIR="_archive"

rm -rf "$ARCHIVE_DIR"
git clone --depth 1 "$REPO_URL" "$ARCHIVE_DIR"
cd "$ARCHIVE_DIR"

# 创建目录结构
mkdir -p "$(dirname "$ARCHIVE_PATH")"

# 复制报告
cp "../$REPORT_FILE" "$ARCHIVE_PATH"

git config user.name "issue-bot"
git config user.email "bot@huaweicloud-mate.dev"
git add "$ARCHIVE_PATH"
git commit -m "$COMMIT_MSG" || echo "No changes to commit"
git push origin main
cd ..
rm -rf "$ARCHIVE_DIR"
echo "Report archived: $ARCHIVE_PATH"
