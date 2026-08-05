#!/usr/bin/env python3
"""治理整改邮件通知脚本

从 GitHub API 实时拉取组织仓库与协作者角色，按负责人（Admin/Maintainer）分组，
为每位负责人生成定制 HTML 整改通知邮件（仅含其关联仓库与角色人员），并通过 SMTP 发送。

用法:
    python governance_email_notify.py          # 发送邮件
    python governance_email_notify.py --dry    # 只生成预览，不发送
"""

import os
import sys
import yaml
import requests
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from email_notify import send_email

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

DRY_RUN = "--dry" in sys.argv


def load_config():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "configs", "governance-email-rules.yml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_all_repos(org):
    repos = []
    page = 1
    while True:
        url = f"{GITHUB_API}/orgs/{org}/repos?per_page=100&page={page}"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print(f"WARN: fetch repos failed: {resp.status_code}")
            break
        data = resp.json()
        if not data:
            break
        for r in data:
            if r.get("archived") or r.get("disabled"):
                continue
            repos.append({
                "name": r["name"],
                "full_name": r["full_name"],
                "visibility": r["visibility"],
                "private": r["private"],
                "pushed_at": r.get("pushed_at"),
                "updated_at": r.get("updated_at"),
                "description": (r.get("description") or "")[:60],
            })
        page += 1
    return repos


def get_collaborators(full_name):
    """返回 {login: role_name}，role_name ∈ admin/maintain/write/triage/read"""
    roles = {}
    page = 1
    while True:
        url = f"{GITHUB_API}/repos/{full_name}/collaborators?per_page=100&page={page}"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        for c in data:
            if c.get("permissions"):
                if c["permissions"].get("admin"):
                    role = "admin"
                elif c["permissions"].get("maintain"):
                    role = "maintain"
                elif c["permissions"].get("push"):
                    role = "write"
                else:
                    role = "triage"
            else:
                role = c.get("role_name", "read")
            roles[c["login"]] = role
        page += 1
    return roles


def collect_data(config):
    org = config["org"]
    repos = get_all_repos(org)
    print(f"Fetched {len(repos)} repos")

    repo_records = []
    for r in repos:
        collaborators = get_collaborators(r["full_name"])
        r["collaborators"] = collaborators
        repo_records.append(r)
        print(f"  {r['full_name']} ({r['visibility']}): {len(collaborators)} collaborators")

    return repo_records


def group_by_person(repo_records):
    """按负责人分组：person -> {repos: [{repo, role, all_roles}]}"""
    persons = {}  # login -> {role, repos:[...]}

    for r in repo_records:
        collabs = r["collaborators"]
        for login, role in collabs.items():
            if role not in ("admin", "maintain"):
                continue
            if login.endswith("[bot]") or "-bot" in login or login == "github-actions":
                continue
            person = persons.setdefault(login, {"repos": []})
            person["repos"].append({
                "repo": r["full_name"],
                "visibility": "Public" if not r["private"] else ("Private" if r["visibility"] == "private" else "Internal"),
                "role": role,
                "all_roles": collabs,
            })
    return persons


def detect_archivable(repo_records, threshold_days):
    """检测长期未更新仓库（pushed_at 距今超过阈值）"""
    now = datetime.now(timezone.utc)
    archivable = []
    for r in repo_records:
        if not r.get("pushed_at"):
            continue
        pushed = datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))
        if (now - pushed).days > threshold_days:
            archivable.append(r)
    return archivable


def fmt_roles(all_roles, target_roles):
    names = [login for login, role in all_roles.items() if role in target_roles]
    return ", ".join(f"@{n}" for n in names) if names else "—（待补充）"


def build_html(config, person_login, person_data, archivable, today):
    cfg = config["remediation"]
    org = config["org"]
    contacts = config["contacts"]
    archive_deadline = (today + timedelta(days=cfg["archive_deadline_days"])).strftime("%Y-%m-%d")
    feedback_deadline = (today + timedelta(days=cfg["feedback_deadline_days"])).strftime("%Y-%m-%d")

    admin_repos = [r for r in person_data["repos"] if r["role"] == "admin"]
    maintain_repos = [r for r in person_data["repos"] if r["role"] == "maintain"]

    # 仓库表
    rows = ""
    for r in person_data["repos"]:
        admins = fmt_roles(r["all_roles"], ["admin"])
        mains = fmt_roles(r["all_roles"], ["maintain"])
        writes = fmt_roles(r["all_roles"], ["write", "triage"])
        rows += (
            f"      <tr>\n"
            f"        <td><code>{r['repo']}</code></td>\n"
            f"        <td>{r['visibility']}</td>\n"
            f"        <td>{admins}</td>\n"
            f"        <td>{mains}</td>\n"
            f"        <td>{writes}</td>\n"
            f"      </tr>\n"
        )

    # 归档清单
    if archivable:
        archive_items = "".join(
            f"        <tr><td><code>{r['full_name']}</code></td><td>{r['visibility']}</td>"
            f"<td>{r.get('pushed_at', '—')[:10]}</td></tr>\n"
            for r in archivable
        )
        archive_section = f"""
    <div class="checklist">
      <div class="checklist-item">
        <div class="icon">1</div>
        <div class="text">
          <strong>归档范围</strong>
          <span class="desc">以下仓库超过 {cfg['archive_threshold_days']} 天无任何更新（commit / Issue / PR / Release 均为零）。</span>
        </div>
      </div>
      <div class="checklist-item">
        <div class="icon">2</div>
        <div class="text">
          <strong>整改期限</strong>
          <span class="desc">自本邮件发出之日起 <strong>{cfg['archive_deadline_days']} 日内</strong>（即 <strong>{archive_deadline} 前</strong>）完成：① 恢复维护；② 书面说明保留理由；③ 主动申请归档。</span>
        </div>
      </div>
      <div class="checklist-item">
        <div class="icon">3</div>
        <div class="text">
          <strong>逾期处理</strong>
          <span class="desc">逾期未回复且未按规范配置人员，将<strong>直接对该仓库执行归档（Archive）处理</strong>。</span>
        </div>
      </div>
    </div>
    <table class="role-table">
      <tr><th style="width:50%">仓库名称</th><th style="width:15%">可见性</th><th style="width:35%">最近推送</th></tr>
{archive_items}
    </table>
"""
    else:
        archive_section = f"""
    <div class="callout" style="background:#dafbe1; border-color:#4ac26b; border-left-color:#1a7f37;">
      <strong>状态良好：</strong>您关联的仓库均处于活跃状态，无长期未更新仓库。
    </div>
"""

    contact_lines = "".join(
        f"      <p>{c['name']}（工号：{c['employee_id']}，邮箱：{c['email']}）</p>\n"
        for c in contacts
    )

    roles_need_attention = "".join(
        f"      <li><strong>{r['repo']}</strong>：角色情况见上表，请核对 Admin 是否超配、Maintainer 是否缺失。</li>\n"
        for r in person_data["repos"]
        if fmt_roles(r["all_roles"], ["admin"]).startswith("—")
        or len([l for l, role in r["all_roles"].items() if role == "admin"]) > 3
        or fmt_roles(r["all_roles"], ["maintain"]) == "—（待补充）"
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>huaweicloud-mate 社区仓库治理规范配置提醒</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f6f8fa;
    color: #1f2328;
    line-height: 1.8;
    padding: 32px 16px;
  }}
  .email-container {{
    max-width: 960px;
    margin: 0 auto;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    overflow: hidden;
  }}
  .header {{
    background: linear-gradient(135deg, #0969da 0%, #0550ae 100%);
    color: #ffffff;
    padding: 40px 40px 32px;
  }}
  .header .tag {{
    display: inline-block;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 20px;
    padding: 4px 14px;
    margin-bottom: 16px;
  }}
  .header h1 {{ font-size: 24px; font-weight: 700; margin-bottom: 8px; }}
  .header .subtitle {{ font-size: 14px; opacity: 0.85; }}
  .meta-bar {{
    background: #f6f8fa;
    border-bottom: 1px solid #d0d7de;
    padding: 16px 40px;
    font-size: 13px;
    color: #656d76;
  }}
  .meta-bar span {{ margin-right: 24px; }}
  .meta-bar strong {{ color: #1f2328; }}
  .body {{ padding: 36px 40px 28px; }}
  .body h2 {{
    font-size: 18px;
    font-weight: 700;
    color: #1f2328;
    margin: 28px 0 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #0969da;
    display: inline-block;
  }}
  .body h2:first-of-type {{ margin-top: 0; }}
  .body h3 {{ font-size: 15px; font-weight: 700; color: #1f2328; margin: 20px 0 8px; }}
  .body p {{ font-size: 14px; color: #3c434d; margin-bottom: 12px; }}
  .body ul, .body ol {{ font-size: 14px; color: #3c434d; margin: 8px 0 16px 4px; padding-left: 22px; }}
  .body li {{ margin-bottom: 6px; }}
  .body strong {{ color: #1f2328; }}
  .body code {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 13px;
    background: #eff1f3;
    color: #cf222e;
    border-radius: 4px;
    padding: 1px 5px;
  }}
  .callout {{
    background: #ddf4ff;
    border: 1px solid #54aeff;
    border-left: 4px solid #0969da;
    border-radius: 6px;
    padding: 14px 18px;
    font-size: 13px;
    color: #1f2328;
    margin: 16px 0 20px;
  }}
  .callout strong {{ color: #0550ae; }}
  .checklist {{ border: 1px solid #d0d7de; border-radius: 8px; overflow: hidden; margin: 12px 0 20px; }}
  .checklist-item {{ display: flex; align-items: flex-start; padding: 14px 16px; border-bottom: 1px solid #eaeef2; font-size: 14px; }}
  .checklist-item:last-child {{ border-bottom: none; }}
  .checklist-item .icon {{
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    border: 2px solid #0969da;
    border-radius: 5px;
    margin-right: 12px;
    margin-top: 1px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    color: #0969da;
  }}
  .checklist-item .text {{ color: #3c434d; }}
  .checklist-item .text strong {{ color: #1f2328; display: block; margin-bottom: 2px; }}
  .checklist-item .text .desc {{ font-size: 13px; color: #656d76; }}
  .role-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 20px;
    font-size: 13px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #d0d7de;
  }}
  .role-table th {{
    background: #f6f8fa;
    text-align: left;
    padding: 10px 14px;
    font-weight: 700;
    color: #1f2328;
    border-bottom: 2px solid #d0d7de;
  }}
  .role-table td {{ padding: 10px 14px; border-bottom: 1px solid #eaeef2; color: #3c434d; }}
  .role-table tr:last-child td {{ border-bottom: none; }}
  .role-table .role-admin {{ color: #cf222e; font-weight: 600; }}
  .role-table .role-maintain {{ color: #1a7f37; font-weight: 600; }}
  .role-table .role-write {{ color: #0550ae; font-weight: 600; }}
  .footer {{
    background: #f6f8fa;
    border-top: 1px solid #d0d7de;
    padding: 24px 40px;
    font-size: 13px;
    color: #656d76;
  }}
  .footer .contact {{ margin-top: 8px; padding-top: 12px; border-top: 1px solid #eaeef2; }}
  .footer .contact a {{ color: #0969da; text-decoration: none; }}
  .signature {{ margin-top: 16px; padding-top: 16px; border-top: 1px solid #eaeef2; font-size: 14px; color: #3c434d; }}
</style>
</head>
<body>
<div class="email-container">

  <div class="header">
    <span class="tag">社区治理 · 整改通知</span>
    <h1>huaweicloud-mate 社区仓库治理规范配置提醒</h1>
    <p class="subtitle">请核对您关联的仓库与角色人员，并按规范完成权限配置整改</p>
  </div>

  <div class="meta-bar">
    <span><strong>收件人：</strong>@{person_login}（仓库管理员 / 维护者）</span>
    <span><strong>发件人：</strong>{config['sender']}</span>
    <span><strong>日期：</strong>{today.strftime('%Y-%m-%d')}</span>
  </div>

  <div class="body">

    <p>@{person_login} 您好：</p>

    <p>为提升社区仓库的规范化治理水平，保障代码质量与协作安全，社区运维团队现启动<strong>仓库治理规范化整改</strong>工作。本次通知为<strong>第一阶段</strong>，重点聚焦仓库管理员与维护者角色的权限配置。请你在规定时间节点前，完成以下工作：① <strong>核对您当前关联的仓库及各角色人员名单</strong>（见第三节）；② 对照权限配置规范完成自查与整改（见第二节）；③ <strong>处理长期未更新仓库</strong>（见第四节）。后续阶段将另行通知分支保护、社区健康文件、CI/CD 等配置要求。</p>

    <h2>一、整改背景</h2>
    <p>当前社区仓库存在权限不明确、分支保护缺失、社区健康文件不完善等问题，给代码安全和社区协作带来隐患。通过本次整改，我们期望达成以下目标：</p>
    <ul>
      <li><strong>权限最小化</strong>：明确各角色职责，按"最小权限"原则分配仓库权限。</li>
      <li><strong>代码安全可控</strong>：启用分支保护，所有变更须经 PR 审核通过后合并。</li>
      <li><strong>社区健康可协作</strong>：补全社区健康文件，降低贡献门槛，规范 Issue / PR 流程。</li>
      <li><strong>自动化保障</strong>：配置 CI/CD 流水线，实现自动化构建、测试与安全检查。</li>
    </ul>

    <h2>二、仓库权限与角色配置规范</h2>
    <p>请管理员按照<strong>"最小权限原则"</strong>重新梳理仓库协作者权限。以下为各角色的推荐配置范围：</p>

    <table class="role-table">
      <tr>
        <th style="width:15%">角色</th>
        <th style="width:35%">权限范围</th>
        <th style="width:25%">适用人员</th>
        <th style="width:25%">配置要求</th>
      </tr>
      <tr>
        <td class="role-admin">Admin（管理员）</td>
        <td>全部管理权限，含危险设置（删除仓库、强制推送等）</td>
        <td>仓库 Owner、社区指定负责人</td>
        <td>数量严格控制在 <strong>1–2 人</strong>；非必要不授予 Admin</td>
      </tr>
      <tr>
        <td class="role-maintain">Maintain（维护者）</td>
        <td>可合并 PR、管理 Issue、推送受保护分支（经审核后）</td>
        <td>核心贡献者、模块负责人</td>
        <td>按模块 / 职责范围分配，控制在 <strong>2–3 人</strong>；<strong>需配置 CODEOWNERS</strong></td>
      </tr>
      <tr>
        <td class="role-write">Write / Triage（写入 / 分类）</td>
        <td>推送非保护分支、管理 Issue 标签与里程碑</td>
        <td>活跃贡献者、社区志愿者</td>
        <td>面向社区开放，定期清理不活跃协作者</td>
      </tr>
    </table>

    <div class="callout">
      <strong>整改要求：</strong>请在 <strong>Settings → Collaborators &amp; Teams</strong> 中逐项排查，移除不必要的高权限账户，将超权协作者降级至匹配角色。使用 Team（团队）进行批量管理优于逐一指派个人。
    </div>

    <h2>三、您的仓库归属与角色人员盘点</h2>
    <p>下表为您当前以 <strong>Admin / Maintain</strong> 角色关联的仓库清单及各仓库角色人员分配情况，请逐一核对：</p>

    <table class="role-table">
      <tr>
        <th style="width:22%">仓库名称</th>
        <th style="width:8%">可见性</th>
        <th style="width:23%">Admin（管理员）</th>
        <th style="width:23%">Maintain（维护者）</th>
        <th style="width:24%">Write / Triage（写入 / 分类）</th>
      </tr>
{rows}
    </table>

    <div class="callout">
      <strong>自查步骤：</strong>
      <ol style="margin:6px 0 0 4px; padding-left:20px;">
        <li>核对上表中您关联的仓库是否完整，是否有遗漏或多出的仓库。</li>
        <li>逐一确认各仓库 Admin / Maintain / Write 角色的人员名单，标注<strong>已离职 / 转岗 / 长期不活跃</strong>的人员。</li>
        <li>检查是否存在<strong>角色缺失</strong>（如某仓库无 Maintainer，或 Admin 仅 1 人无备份）的情况。</li>
        <li>如发现信息有误，请于 <strong>{feedback_deadline} 前</strong>反馈至社区运维团队，我们将更新台账。</li>
      </ol>
    </div>

    <div class="callout" style="background:#fff8c5; border-color:#d4a72c; border-left-color:#9a6700;">
      <strong>重点提醒：</strong>如发现您名下有<strong>不再活跃维护</strong>的仓库，请及时将 Admin 权限移交至接任人员，或申请归档（Archive）该仓库，避免长期无人管理的"僵尸仓库"。
    </div>

    <h2>四、长期未更新仓库归档处理</h2>
    <p>经社区运维团队盘点，存在部分仓库长期无任何代码提交、Issue 活动或 Release 发布，处于长期停滞状态。为降低安全风险、保持社区仓库列表整洁，现对这类仓库启动<strong>归档清理</strong>程序：</p>
{archive_section}
    <div class="callout" style="background:#ffebe9; border-color:#ff8182; border-left-color:#cf222e;">
      <strong style="color:#cf222e;">重要提醒：</strong>请务必在 <strong>{archive_deadline} 前</strong>完成响应。逾期未处理的仓库将被<strong>自动归档</strong>，届时代码虽不会丢失，但仓库将进入只读状态，所有协作功能关闭。
    </div>

    <div class="callout" style="background:#dafbe1; border-color:#4ac26b; border-left-color:#1a7f37;">
      <strong>整改说明：</strong>本次整改旨在提升社区仓库的规范性和安全性，而非追溯责任。请积极配合，如在配置过程中遇到技术问题或对权限分配有疑问，请随时联系社区运维团队。
    </div>

    <div class="signature">
      <p>感谢您的配合与支持！</p>
      <p style="margin-top:8px;">{config['sender']}<br>{today.strftime('%Y 年 %m 月 %d 日')}</p>
    </div>

  </div>

  <div class="footer">
    <p>本邮件由社区治理系统自动发出，请勿直接回复。如有疑问请联系社区运维团队。</p>
    <div class="contact">
      <p><strong>请联系管理员：</strong></p>
{contact_lines}
    </div>
  </div>

</div>
</body>
</html>"""
    return html


def main():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN is required (set in .env or environment)")
        sys.exit(1)

    config = load_config()
    repo_records = collect_data(config)
    persons = group_by_person(repo_records)
    today = datetime.now(timezone.utc)
    archivable = detect_archivable(repo_records, config["remediation"]["archive_threshold_days"])

    if not persons:
        print("No Admin/Maintainer found, nothing to send")
        return

    print(f"\nLong-inactive repos: {len(archivable)}")
    for r in archivable:
        print(f"  - {r['full_name']} (last push {r.get('pushed_at','')[:10]})")

    sent_count = 0
    for login, data in sorted(persons.items()):
        email = config.get("emails", {}).get(login, "")
        subject = f"[huaweicloud-mate 社区治理整改] 仓库权限配置核对通知 — {today.strftime('%Y-%m-%d')}"
        html_body = build_html(config, login, data, archivable, today)

        if DRY_RUN:
            outdir = os.path.join(os.getcwd(), "output")
            os.makedirs(outdir, exist_ok=True)
            with open(os.path.join(outdir, f"governance_email_{login}.html"), "w", encoding="utf-8") as f:
                f.write(html_body)
            print(f"[DRY] {login} -> {email or 'NO-EMAIL'} ({len(data['repos'])} repos)")
            continue

        if not email:
            print(f"SKIP {login}: no email configured")
            continue

        ok = send_email(subject=subject, body=html_body, to_emails=[email], is_html=True)
        if ok:
            sent_count += 1
        print(f"  {login} -> {email}: {'sent' if ok else 'FAILED'} ({len(data['repos'])} repos)")

    print(f"\nDone. Sent: {sent_count}/{len(persons)}")


if __name__ == "__main__":
    main()
