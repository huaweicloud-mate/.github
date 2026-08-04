# huaweicloud-mate Issues 自动化管理流程

## 完整流程

```
Issue 创建（GitHub / GitCode）
    ↓
┌──────────────────── GitHub ────────────────────┐  ┌────────────── GitCode ──────────────┐
│                                                 │  │                                     │
│ Issue Bot → 自动打标签 + 分配负责人              │  │ gitcode_triage → API 打标签 + 评论   │
│     ↓                                           │  │     ↓                               │
│ SLA 监控（每小时）                               │  │ SLA 监控（每小时）                    │
│     ↓                                           │  │     ↓                               │
│ 超时 → 打标签 + 飞书卡片 + 邮件                  │  │ 超时 → 飞书卡片 + 邮件                │
│     ↓                                           │  │     ↓                               │
│ 状态流转: pending → triaged → resolved          │  │ Stale: 过期 → 自动关闭               │
│     ↓                                           │  │                                     │
│ Stale: 过期 → 自动关闭                          │  │                                     │
│     ↓                                           │  │                                     │
│ 周报/月报/SLA日报 → 飞书卡片 + HTML 邮件        │  │ 合并到同一报表                        │
└─────────────────────────────────────────────────┘  └─────────────────────────────────────┘
```

---

## 一、GitHub Issue 分类 / Triage

### 触发方式
- Issue Bot（`actions/issue-bot/`）在 Issue 创建时自动运行（已有，含飞书审批通知、斜杠命令）
- `triage-issue.yml` 通过 `issue-bot` Action 扩展分类能力

### 自动打标签规则

| 触发条件 | 标签 | 说明 |
|---------|------|------|
| 标题/正文含关键词 | `type/bug` `type/feature` `type/documentation` `type/question` | 关键字匹配 |
| 严重性关键词 | `priority/critical` `priority/high` `priority/medium` `priority/low` | 自动分析 |
| 领域关键词 | `area/api` `area/web` `area/ci-cd` 等 | 根据 `triage-rules.yml` |

### 自动分配负责人

| 标签/领域 | 负责人 |
|-----------|--------|
| `area/api` | @api-maintainer |
| `area/web` | @web-maintainer |
| `area/ci-cd` | @devops-maintainer |
| `type/bug` + `priority/critical` | @tech-lead |
| 无匹配 | @default-triage |

### 关键文件

| 文件 | 作用 |
|------|------|
| `actions/issue-bot/issue_bot.py` | Issue Bot 核心脚本（已有） |
| `configs/triage-rules.yml` | 分类规则（标签/负责人映射） |
| `workflows/triage-issue.yml` | Triage 触发器 |

---

## 二、GitHub Issue 生命周期

### 状态流转

```
status/pending          → Issue 新建，待 triage
status/triaged          → 已分类 + 已分配
status/in-progress      → 开发中（PR 关联自动标记）
status/resolved         → 已修复（PR 合并自动标记）
status/completed        → 已验证 / 管理员关闭
```

### 自动状态转换

| 事件 | 状态变更 | 触发 |
|------|---------|------|
| Issue Bot 分类完成 | `pending` → `triaged` | Issue Bot |
| PR 链接 Fixes/Closes #N | `triaged` → `in-progress` | GitHub 联动 |
| 关联 PR 合并 | `in-progress` → `resolved` | workflow |
| 手动关闭 | 任意 → `completed` | 管理员 |

### Stale 处理

| 类型 | 过期天数 | 关闭缓冲 |
|------|---------|---------|
| `type/bug` | 60 天 | 14 天 |
| `type/feature` | 90 天 | 14 天 |
| `type/question` | 30 天 | 7 天 |
| `type/documentation` | 180 天 | 14 天 |
| `priority/critical` | 365 天 | 30 天 |

### 关键文件

| 文件 | 作用 |
|------|------|
| `workflows/stale.yml` | Stale bot 工作流 |
| `configs/stale-rules.yml` | 过期天数配置 |
| `workflows/status-transition.yml` | 状态流转工作流 |

---

## 三、通知系统（飞书 + 邮件）

### 双通道通知

所有事件同时发送飞书卡片和 HTML 邮件：

| 事件 | 飞书 | 邮件 |
|------|:---:|:---:|
| Issue 新建/关闭 | 分段卡片 | HTML |
| SLA 预警/违约/升级 | 卡片 + 按钮 | HTML |
| Issue 即将过期 (stale) | 卡片 | HTML |
| 周报/月报/SLA日报 | 分段卡片+表格 | HTML 表格 |

### 飞书通知

- 通过飞书 Open API 发送 DM 卡片消息
- 报表：分段结构化卡片，表格用 `lark_md` 渲染
- 告警：颜色区分（红=违约, 橙=预警, 蓝=新建, 绿=关闭）
- 管理员：ou_f3d92a9ef16eba823ed80e8107fb3763（张爽）

### 邮件通知

- 通过 SMTP（QQ 邮箱 `smtp.qq.com:587`）发送
- HTML 格式：蓝色渐变标题栏、交替行颜色表格、红色标记超时数据
- 收件人：114271379@qq.com
- 后续可按维护者邮箱映射分发

### 关键文件

| 文件 | 作用 |
|------|------|
| `workflows/feishu-notify.yml` | 可复用飞书+邮件通知工作流 |
| `workflows/issue-notify.yml` | Issue 事件 → 通知触发 |
| `scripts/feishu_notify.py` | 飞书卡片发送 |
| `scripts/email_notify.py` | SMTP 邮件发送（Markdown→HTML） |
| `configs/feishu-rules.yml` | 通知规则配置 |

---

## 四、GitCode Issue 自动化管理

### 说明
- GitCode Issue **在 GitCode 原生平台独立管理**，不同步到 GitHub
- 通过 GitCode API v5 远程操作标签、评论、状态
- API 基地址：`https://api.gitcode.com/api/v5`（GitHub 风格端点）
- 端点示例：`GET /orgs/hd-vector/repos`、`GET /repos/{owner}/{repo}/issues`、`PATCH /repos/{owner}/{repo}/issues/{number}`
- `hd-vector` 组织下所有仓库自动覆盖

### 功能模块

| 模块 | 频率 | 功能 |
|------|------|------|
| **Triage** | 每 6 小时 | 扫描新 Issue → 关键字分类 → API 打标签 + 评论 |
| **SLA 监控** | 每小时 | 超时检测 → 飞书 + 邮件告警 |
| **SLA 日报** | 工作日 08:00 | 超时 Issue 清单 → 飞书 + 邮件 |
| **Stale 管理** | 每天 | 过期 Issue 打 stale → 14 天后 API 关闭 |

### GitCode Triage 分类规则

与 GitHub 规则一致：
- `type/bug`：bug, 错误, crash, 崩溃, 报错
- `type/feature`：feature, 功能, 新增, enhancement
- `type/question`：question, 问题, 咨询
- `type/documentation`：doc, 文档, documentation
- 优先级：critical(urgent/紧急) → high(important/重要) → low(minor/优化) → 默认 medium

### GitCode Stale 规则

| 类型 | 过期天数 | 关闭缓冲 |
|------|---------|---------|
| `type/bug` | 60 天 | 14 天 |
| `type/feature` | 90 天 | 14 天 |
| `type/question` | 30 天 | 14 天 |
| `type/documentation` | 180 天 | 14 天 |
| `priority/critical` | 365 天 | 14 天 |

### 关键文件

| 文件 | 作用 |
|------|------|
| `workflows/gitcode-triage.yml` | GitCode Triage 触发器 |
| `workflows/gitcode-sla.yml` | GitCode SLA 监控 + 日报 |
| `workflows/gitcode-stale.yml` | GitCode Stale 管理 |
| `scripts/gitcode_triage.py` | GitCode 分类打标签脚本 |
| `scripts/gitcode_sla.py` | GitCode SLA 检测脚本 |
| `scripts/gitcode_stale.py` | GitCode 过期关闭脚本 |
| `scripts/gitcode_stats.py` | GitCode 统计抓取（周报用） |

---

## 五、Issue 报表

### 报表类型

| 报表 | 频率 | 统计范围 | 内容 | 发送 |
|------|------|---------|------|------|
| **周报** | 每周一 09:00 UTC | 上周一 ~ 上周日（回顾模式） | 新建/关闭/净变化、SLA 达标率、类型分布、仓库明细、GitCode 统计 | 飞书+邮件 |
| **月报** | 每月 1 号 | 上月 1 号 ~ 月末（回顾模式） | 月度新建/关闭率、类型占比、仓库排行 TOP10、GitCode 统计 | 飞书+邮件 |
| **SLA 日报** | 工作日 08:00 UTC | 当前时刻 | 超时 Issue 清单（含详情）、SLA 达标率 | 飞书+邮件 |

### 报表示例

```
# huaweicloud-mate Issues 周报
**2026-W31 | 07.27 - 08.02** | 生成时间: 2026-08-03 01:39 UTC

## 概览
| 指标 | 本周数值 | 总活跃/累计 |
|------|---------|------------|
| 本周新建 | 4 | / |
| 本周关闭 | 3 | / |
| 本周净变化 | +1 | / |        ← 新建 - 关闭
...
```

### 报告归档

所有报表自动归档到私有仓库 `huaweicloud-mate/reports`，按年月分类：

```
reports/
└── 2026/
    ├── weekly/w31.md
    ├── monthly/2026-07.md
    └── sla/2026-08-03.md
```

### 统计维度

| 维度 | GitHub | GitCode |
|------|:------:|:-------:|
| Issue 总数/开启/关闭 | ✅ | ✅ |
| 按类型/优先级分布 | ✅ | ✅ |
| SLA 达标率 | ✅ | ✅ |
| 仓库排行 | ✅ | ✅ |
| 净变化（新建-关闭） | ✅ | ✅ |

### 关键文件

| 文件 | 作用 |
|------|------|
| `workflows/issue-stats.yml` | 统计+报表触发器 |
| `workflows/weekly-report.yml` | 周报触发 + 归档 |
| `workflows/monthly-report.yml` | 月报触发 + 归档 |
| `workflows/sla-daily.yml` | SLA 日报触发 + 归档 |
| `scripts/github_stats.py` | GitHub Issue 统计（自然周/日历月） |
| `scripts/gitcode_stats.py` | GitCode Issue 统计抓取 |
| `scripts/stats_report.py` | 合并生成报表 + 双通道发送 + 保存文件 |
| `scripts/archive_report.sh` | 归档脚本（推送至 reports 仓库） |
| `templates/report-weekly.md` | 周报模板 |
| `templates/report-monthly.md` | 月报模板 |

---

## 六、SLA 标准

### GitHub

| 优先级 | 首次响应时限 | 解决时限 | 升级时限 |
|--------|------------|---------|---------|
| `priority/critical` | 4 小时 | 1 天 | 8 小时 |
| `priority/high` | 8 小时 | 3 天 | 24 小时 |
| `priority/medium` | 24 小时 | 7 天 | 3 天 |
| `priority/low` | 48 小时 | 30 天 | 14 天 |

### GitCode（相同标准）

| 优先级 | 首次响应时限 | 解决时限 | 升级时限 |
|--------|------------|---------|---------|
| critical | 4 小时 | 1 天 | 8 小时 |
| high | 8 小时 | 3 天 | 24 小时 |
| medium | 24 小时 | 7 天 | 3 天 |
| low | 48 小时 | 30 天 | 14 天 |

### 关键文件

| 文件 | 作用 |
|------|------|
| `workflows/sla-monitor.yml` | GitHub SLA 监控（每小时） |
| `workflows/gitcode-sla.yml` | GitCode SLA 监控（每小时） |
| `scripts/sla_monitor.py` | GitHub SLA 检测+告警 |
| `scripts/gitcode_sla.py` | GitCode SLA 检测+告警 |
| `configs/sla-rules.yml` | SLA 时限配置 |

---

## 七、全部 Workflow 触发总览

| Workflow | 触发方式 | 频率 |
|----------|---------|------|
| `triage-issue.yml` | Issue opened | 实时 |
| `issue-notify.yml` | Issue opened/closed/labeled | 实时 |
| `feishu-notify.yml` | workflow_call / workflow_dispatch | 按需 |
| `sla-monitor.yml` | schedule | 每小时 |
| `stale.yml` | schedule | 每天 02:00 UTC |
| `status-transition.yml` | PR opened/closed + issue closed | 实时 |
| `issue-stats.yml` | schedule / workflow_dispatch | 每周一 09:00 UTC |
| `weekly-report.yml` | schedule | 每周一 09:00 UTC |
| `monthly-report.yml` | schedule | 每月 1 号 |
| `sla-daily.yml` | schedule | 工作日 08:00 UTC |
| `gitcode-triage.yml` | schedule | 每 6 小时 |
| `gitcode-sla.yml` | schedule | 每小时 |
| `gitcode-stale.yml` | schedule | 每天 03:00 UTC |

---

## 八、组织 Secrets

| Secret | 用途 | 级别 |
|--------|------|------|
| `FEISHU_APP_ID` | 飞书应用 ID | 组织级 + .github |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | 组织级 + .github |
| `FEISHU_ADMIN_OPEN_ID` | 管理员 open_id（ou_f3dxxx） | 组织级 + .github |
| `SMTP_HOST` | QQ 邮箱 SMTP 服务器（smtp.qq.com） | 组织级 + .github |
| `SMTP_PORT` | SMTP 端口（587） | 组织级 + .github |
| `SMTP_USER` | SMTP 账号（114271379@qq.com） | 组织级 + .github |
| `SMTP_PASS` | SMTP 授权码（QQ 邮箱） | 组织级 + .github |
| `EMAIL_REPORT_TO` | 报表接收邮箱（114271379@qq.com） | 组织级 + .github |
| `GITCODE_TOKEN` | GitCode API Token | 组织级 + .github |
| `GITHUB_TOKEN` | GitHub API | 默认提供 |

---

## 九、管理员操作速查

```powershell
# === GitHub ===
# 查看超时 Issue
gh issue list -R huaweicloud-mate/<repo> -l "sla/breach"

# 查看待处理 Issue
gh issue list -R huaweicloud-mate/<repo> -l "status/pending"

# 查看 escalation Issue
gh issue list -R huaweicloud-mate/<repo> -l "escalation"

# 手动触发统计报表
gh workflow run issue-stats.yml -R huaweicloud-mate/.github

# 手动触发 SLA 检查
gh workflow run sla-monitor.yml -R huaweicloud-mate/.github

# 手动测试飞书通知
gh workflow run feishu-notify.yml -R huaweicloud-mate/.github -f event=test -f subject="测试" -f body="内容"

# === GitCode ===
# 手动触发 GitCode Triage
gh workflow run gitcode-triage.yml -R huaweicloud-mate/.github

# 手动触发 GitCode SLA
gh workflow run gitcode-sla.yml -R huaweicloud-mate/.github

# 手动触发 GitCode Stale
gh workflow run gitcode-stale.yml -R huaweicloud-mate/.github
```

---

## 十、标签体系

### GitHub 标准标签

| 标签 | 用途 | GitCode 对应 |
|------|------|:-----------:|
| `type/bug` | Bug 报告 | ✅ |
| `type/feature` | 功能请求 | ✅ |
| `type/documentation` | 文档相关 | ✅ |
| `type/question` | 问题咨询 | ✅ |
| `priority/critical` | 紧急 | ✅ |
| `priority/high` | 高 | ✅ |
| `priority/medium` | 中 | ✅ |
| `priority/low` | 低 | ✅ |
| `status/pending` | 待处理 | - |
| `status/triaged` | 已分类 | - |
| `status/in-progress` | 进行中 | - |
| `status/resolved` | 已解决 | - |
| `status/completed` | 已完成 | - |
| `status/stale` | 即将过期 | ✅ |

### 自动化专用标签

| 标签 | 用途 |
|------|------|
| `sla/breach` | SLA 已违约 |
| `sla/warning` | SLA 即将违约 |
| `escalation` | 已升级 |

---

## 十一、待改进项

- [ ] 按维护者邮箱分发通知（当前统一发管理员）
- [ ] GitCode `GITCODE_TOKEN` 权限确认（当前 401）
- [ ] Issue 趋势图表（环比变化）
- [ ] 飞书 bot 交互命令（/assign, /priority 等扩展）
