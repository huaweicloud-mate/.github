#!/usr/bin/env python3
"""邮件发送脚本 - 通过 SMTP 发送报告邮件"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime, timezone


def send_email(subject, body, to_emails=None, is_html=False):
    smtp_host = os.environ.get("SMTP_HOST", "smtp.qq.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        print("WARNING: SMTP credentials not configured, skipping email")
        return False

    if not to_emails:
        to_emails = [s.strip() for s in os.environ.get("EMAIL_REPORT_TO", "").split(",") if s.strip()]

    if not to_emails:
        print("No recipients, skipping email")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = smtp_user
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = Header(subject, "utf-8")
    msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    if is_html:
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        html_body = f"""<html>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; max-width: 700px; margin: 0 auto;">
<div style="background-color: #0366d6; color: white; padding: 16px; border-radius: 8px 8px 0 0;">
    <h2 style="margin:0;">huaweicloud-mate Issue Report</h2>
</div>
<div style="border: 1px solid #e1e4e8; padding: 20px; border-radius: 0 0 8px 8px; background: #fff;">
    <pre style="white-space: pre-wrap; font-family: Consolas, monospace; font-size: 13px; line-height: 1.5;">{body}</pre>
</div>
<div style="color: #586069; font-size: 11px; margin-top: 12px; text-align: center;">
    huaweicloud-mate Issue Bot · Auto-generated
</div>
</body>
</html>"""
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_emails, msg.as_string())
        server.quit()
        for addr in to_emails:
            print(f"Email sent to {addr}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def main():
    subject = os.environ.get("SUBJECT", "Issue Report")
    body = os.environ.get("BODY", "")

    if not body:
        print("No body content, skipping")
        return

    to = os.environ.get("EMAIL_TO", "")
    to_list = [t.strip() for t in to.split(",") if t.strip()] if to else None
    is_html = os.environ.get("EMAIL_HTML", "0") == "1"

    send_email(subject, body, to_list, is_html)


if __name__ == "__main__":
    main()
