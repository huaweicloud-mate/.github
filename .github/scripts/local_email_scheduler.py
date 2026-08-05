#!/usr/bin/env python3
"""本地常驻定时任务 - 工作日 09:00 发送治理整改通知邮件

部署方式（Windows）：
    1. 复制 .env.example 为 .env，填入 SMTP 凭据
    2. python .github/scripts/local_email_scheduler.py
    3. （可选）使用 pythonw 后台运行，或用计划任务开机自启

用法：
    python local_email_scheduler.py           # 常驻，工作日 09:00 发送
    python local_email_scheduler.py --once    # 立即运行一次后退出（用于测试/手动补发）
"""

import os
import sys
import time
import logging
from datetime import datetime

from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("governance-email-scheduler")

# 脚本位于 .github/scripts/，仓库根在其上级
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, ".github", "scripts"))

# 加载本地 .env（SMTP 凭据），避免提交到 git
dotenv_path = os.path.join(REPO_ROOT, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    log.info("Loaded local .env")
else:
    log.warning(".env not found at %s — SMTP will not be configured", dotenv_path)

import governance_email_notify as gen

RUN_HOUR = int(os.environ.get("RUN_HOUR", "9"))
RUN_MINUTE = int(os.environ.get("RUN_MINUTE", "0"))
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "30"))


def is_workday(d):
    return d.weekday() < 5  # 0=Mon ... 4=Fri


def run_job():
    log.info("Triggering governance email notification run")
    try:
        gen.main()
    except Exception:
        log.exception("Governance email job failed")
        return False
    log.info("Governance email job finished")
    return True


def run_once():
    if not os.environ.get("SMTP_USER") or not os.environ.get("SMTP_PASS"):
        log.error("SMTP credentials missing in .env — nothing sent")
        return 1
    return 0 if run_job() else 1


def run_once_dry():
    log.info("Dry run (generate previews only)")
    gen.DRY_RUN = True
    return 0 if run_job() else 1


def main():
    log.info(
        "Scheduler started. Will run at %02d:%02d on workdays (poll every %ds)",
        RUN_HOUR, RUN_MINUTE, POLL_SECONDS,
    )

    if not os.environ.get("SMTP_USER") or not os.environ.get("SMTP_PASS"):
        log.warning("SMTP credentials not set — jobs will run but emails will be skipped")

    last_run_key = None

    while True:
        now = datetime.now()
        key = now.strftime("%Y-%m-%d")
        if is_workday(now) and now.hour == RUN_HOUR and now.minute == RUN_MINUTE:
            if last_run_key != key:
                run_job()
                last_run_key = key
                time.sleep(61)  # 跳过本分钟的重复触发
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    if "--dry" in sys.argv:
        sys.exit(run_once_dry())
    if "--once" in sys.argv:
        sys.exit(run_once())
    main()
