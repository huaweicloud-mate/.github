# huaweicloud GitHub 社区治理整改月度计划 v4.0

> 版本: v4.0（8月聚焦版）
> 编制日期: 2026-08-03
> 数据基准: 2026-07-24 盘点报告（本版核验修正）
> 目标组织: huaweicloud（155活跃仓库）
> 策略: 按风险等级逐层推进，优先自动化批量处理

---

## 一、现状基线（已核验）

| 指标 | 当前值 | 目标值（8月底） | 风险 |
|------|--------|----------------|------|
| License 缺失（活跃） | 31个 (20.0%) | 0 | 🔴 无License=所有权利保留，用户不可合法使用 |
| 单人维护仓库 | 67个 (43.2%) | ≤10 | 🔴 唯一维护者离职=仓库失联 |
| 分支保护 | 24/155 (15.5%) | Stars≥20仓库100% (38个) | 🔴 无保护=任何人可直推main |
| 要求PR Review | 10/155 (6.5%) | Stars≥20仓库100% | 🔴 无Review=代码变更无审查 |
| CONTRIBUTING.md | 4/155 (2.6%) | Stars≥50仓库100% (17个) | 🟡 新贡献者不知如何参与 |
| SECURITY.md | 3/155 (1.9%) | Stars≥50仓库100% | 🟡 安全漏洞无人报告 |
| CODE_OF_CONDUCT.md | 3/155 (1.9%) | Stars≥50仓库100% | 🟡 社区冲突无处理依据 |
| Issue模板 | 6/155 (3.9%) | Stars≥50仓库100% | 🟡 用户提交Issue格式混乱 |
| PR模板 | 4/155 (2.6%) | Stars≥50仓库100% | 🟡 PR信息不完整 |
| Issues禁用 | 4个 | 0 | 🟡 用户反馈通道关闭 |
| 非标准分支名 | 7个 | 0 | 🟡 CI/CD配置混乱 |
| Dependabot | 4/155 (2.6%) | Stars≥50仓库100% | 🟡 依赖漏洞无人感知 |
| CodeQL | 4/155 (2.6%) | Stars≥50仓库100% | 🟡 代码安全扫描为零 |
| 安全告警(Critical) | 135个 | ≤10 | 🔴 已知可利用漏洞未修复 |

**成熟度评分：加权总分 36/100（较差）**

---

## 二、执行节奏总览

```
Step 0 (D0-D2)  定标：组织级模板(.github仓库) — 先立规矩
W1 (D3-D7)      P0 止损：License + 安全告警 + Issues启用
W2 (D8-D14)     P0 止损：分支保护 + 单人维护 + 分支名统一
W3 (D15-D21)    P1 筑基：社区文件补全(Stars≥50) + Dependabot
W4 (D22-D30)    P1 筑基：CodeQL + 自动巡检上线 + 月度报告
```

---

## 周进展（8月第1周 · D1-D2）

> 更新日期: 2026-08-04

### 本周完成

| 事项 | 状态 | 说明 |
|------|:--:|------|
| **huaweicloud-mate/.github 治理规范** | ✅ | GOVERNANCE.md 已推送，定义三级准入体系 + 9子类型→4等级 |
| **huaweicloud-mate/.github 模板补齐** | ✅ | dependabot.yml / governance-audit.yml / bug_report.yml / feature_request.yml 已推送 |
| **Stale 集中管理改造** | ✅ | stale_manager.py + workflow + 存量清理 + 建仓脚本去重（同步推送到 huaweicloud-mate） |
| **建仓流程文档** | ✅ | v1.1 已发布，按 repo_creator.py (1102行) 最新逻辑校准 |
| **月度计划** | ✅ | v4.0 含 Step 0 定标 + W1-W4 分阶段计划 |
| **组织模板文件** | 📦 | huaweicloud/.github (14个) + repository-requests (5个) 本地就绪 |

### 关键产出

- **建仓流程文档**: https://github.com/huaweicloud-mate/.github/blob/main/docs/建仓流程文档.md
- **治理规范**: https://github.com/huaweicloud-mate/.github/blob/main/GOVERNANCE.md
- **月度计划**: `/home/zhangshuang/github-community-governance/月度计划/huaweicloud-governance-monthly-plan.md`
- **模板文件**: `/home/zhangshuang/github-community-governance/组织模板/`
- **批量脚本**: `/home/zhangshuang/github-community-governance/月度计划/scripts/`

### 待推进（D2 内）

| 事项 | 优先级 |
|------|:--:|
| 创建 `huaweicloud/.github` 仓库 + 推送14个模板文件 | 🔴 |
| 创建 `huaweicloud/repository-requests` 仓库 + 推送建仓机器人 | 🔴 |
| 配置 BOT_TOKEN / Feishu Secrets | 🟡 |

### 阻赛

无。

---

## Step 0 — 定标：组织级模板（D0-D2）

### 目标
在整改存量仓库之前，先建立组织级的"标准配置"——`huaweicloud/.github` 仓库。

### 原理
GitHub 自动将 `.github` 仓库中的社区文件作为所有仓库的**默认模板**。仓库无自定义模板时自动继承组织级模板。

- Issue Templates → 仓库没有自己的模板时，自动使用 .github 的
- PR Template → 同理
- CONTRIBUTING.md / SECURITY.md / CoC → 仓库没有时，提示链接到 .github 的
- profile/README.md → 显示在 github.com/huaweicloud 组织首页

### 操作清单

| 文件 | 说明 | 状态 |
|------|------|:--:|
| 创建 `huaweicloud/.github` 仓库 | `gh repo create huaweicloud/.github --public` | ⬜ |
| README.md | 仓库说明 + 治理规范总览 | ✅ 已准备 |
| LICENSE | Apache-2.0 | ✅ 已准备 |
| CONTRIBUTING.md | 组织级贡献指南 | ✅ 已准备 |
| SECURITY.md | 安全漏洞报告流程（mailto:） | ✅ 已准备 |
| CODE_OF_CONDUCT.md | 贡献者行为准则 | ✅ 已准备 |
| profile/README.md | 组织首页展示 | ✅ 已准备 |
| .github/ISSUE_TEMPLATE/bug_report.yml | Bug报告表单 | ✅ 已准备 |
| .github/ISSUE_TEMPLATE/feature_request.yml | 功能请求表单 | ✅ 已准备 |
| .github/ISSUE_TEMPLATE/config.yml | 禁用空白Issue | ✅ 已准备 |
| .github/PULL_REQUEST_TEMPLATE.md | PR模板 | ✅ 已准备 |
| .github/dependabot.yml | 依赖更新配置 | ✅ 已准备 |
| .github/workflows/stale.yml | 过期Issue/PR自动清理 | ✅ 已准备 |
| .github/workflows/governance-audit.yml | 月度治理巡检 | ✅ 已准备 |

**模板文件位置：** `/home/zhangshuang/github-community-governance/组织模板/huaweicloud-dotgithub/`

### 完成后效果
- 新建仓库自动获得 Issue/PR 模板和社区文件
- 存量仓库可以引用 .github 仓库的模板（通过 checkout 或直接复制）
- 组织首页 (github.com/huaweicloud) 将显示 profile/README.md 内容
- Dependabot 和 Stale bot 配置可供仓库直接引用
- 月度巡检自动运行，产出治理报告

---

## 三、W1 — 止损（D3-D7）

### 目标：消除法律风险 + 安全紧急项 + 打通反馈通道

### 3.1 P0-1：License 补全（31个仓库）

**策略：** 所有仓库统一 Apache-2.0（与组织98个已有Apache仓库一致）

**批量脚本：**
```bash
#!/bin/bash
# 为无License仓库添加 Apache-2.0 LICENSE文件
REPOS=(
  cce-cluster-credentials deploy-cce-workflow-sample
  deploy-ecs-workflow-sample deploy-functiongraph-action
  deploy-functiongraph-workflow-sample devspace-devbridge
  dls-example huawei-qingtian huaweicloud-iot-device-sdk-c-tiny
  huaweicloud-iot-device-sdk-kotlin huaweicloud-iot-device-sdk-rust
  huaweicloud-iot-device-sdk-swift huaweicloud-iot-edge-sdk-c
  huaweicloud-iot-edge-sdk-go huaweicloud-iot-edge-sdk-java
  huaweicloud-lts-sdk-cpp huaweicloud-lts-sdk-dotnet
  huaweicloud-lts-sdk-java huaweicloud-lts-sdk-php
  huaweicloud-lts-sdk-python huaweicloud-mrs-example
  huaweicloud-sdk-cpp-v3 huaweicloud-sdk-nodejs-v3
  huaweicloud-sdk-ruby-v3 Maven-cloudartifact-action
  oasis scp-remote-action spring-cloud-huawei-samples
  ssh-remote-action terraformdocs VM-placement-dataset
)

LICENSE_URL="https://www.apache.org/licenses/LICENSE-2.0.txt"

for repo in "${REPOS[@]}"; do
  echo "处理: $repo"
  # 方式1: 通过 GitHub API 创建文件
  curl -s -X PUT "https://api.github.com/repos/huaweicloud/$repo/contents/LICENSE" \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    -d "{\"message\":\"docs: add Apache-2.0 LICENSE\",\"content\":\"$(curl -s $LICENSE_URL | base64 -w0)\"}" \
    | jq -r '.content.html_url // .message'
done
```

**完成标准：** 31/31仓库有LICENSE，且GitHub显示Apache-2.0

### 3.2 P0-2：启用Issues（4个仓库）

```bash
# 逐一启用 Issues
for repo in bosh-deployment cf-deployment cloud-custodian CloudResetPwdAgent; do
  gh api -X PATCH "repos/huaweicloud/$repo" -f has_issues=true
  echo "✓ $repo Issues已启用"
done
```

**注意：** cloud-custodian (20★) Issues被禁用需确认原因

### 3.3 P0-3：修复Critical安全告警（优先Top5仓库）

| 仓库 | Critical | 负责人 |
|------|----------|--------|
| maxwell-dis-plugin | 23 | |
| huaweicloud-cs-sdk | 22 | |
| ModelArts-Lab | 14 | |
| huaweicloud-sdk-java-frs | 11 | |
| packer-plugin-huaweicloud | 9 | |

**操作：** 联系各仓库Owner→Dependabot自动PR合并→验证告警归零

---

## 四、W2 — 止损（D8-D14）

### 目标：建立代码安全底线 + 消除单点故障

### 4.1 P0-4：Stars≥20仓库分支保护（22个未保护仓库）

**目标仓库：**
ModelArts-Lab, cloudeye-exporter, huaweicloud-sdk-python-obs, huaweicloud-sdk-java-obs, huaweicloud-sdk-c-obs, huaweicloud-sdk-go-obs, huaweicloud-sdk-php-obs, huaweicloud-sdk-nodejs-obs, huaweicloud-sdk-dotnet-obs, huaweicloud-sdk-browserjs-obs, huaweicloud-csi-driver, huaweicloud-obs-obsfs, huaweicloud-fpga, huaweicloud-cs-sdk, elb-toa, dls-example, trace_generation_rnn, huaweicloud-iot-device-sdk-android, cloud-custodian, cloudeye-grafana, HiLens-Lab, HUAWEICloudPublicDataset

**保护规则（最低标准）：**
- require PR before merging ✓
- require 1 approval ✓
- dismiss stale reviews ✓
- require status checks (如已有CI) ✓

```bash
# 批量设置分支保护（仅public仓库，free plan私有仓库不支持）
for repo in ModelArts-Lab cloudeye-exporter huaweicloud-sdk-python-obs huaweicloud-sdk-java-obs huaweicloud-sdk-c-obs huaweicloud-sdk-go-obs huaweicloud-sdk-php-obs huaweicloud-sdk-nodejs-obs huaweicloud-sdk-dotnet-obs huaweicloud-sdk-browserjs-obs huaweicloud-csi-driver huaweicloud-obs-obsfs huaweicloud-fpga huaweicloud-cs-sdk elb-toa dls-example trace_generation_rnn huaweicloud-iot-device-sdk-android cloud-custodian cloudeye-grafana HiLens-Lab HUAWEICloudPublicDataset; do
  BRANCH=$(gh api "repos/huaweicloud/$repo" --jq '.default_branch')
  gh api -X PUT "repos/huaweicloud/$repo/branches/$BRANCH/protection" \
    -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
    -f enforce_admins=false \
    -f restrictions=null \
    -f allow_force_pushes=false \
    -f allow_deletions=false
  echo "✓ $repo ($BRANCH) 分支保护已配置"
done
```

### 4.2 P0-5：分支名统一（7个非标准分支）

| 仓库 | 当前分支 | 目标分支 |
|------|----------|----------|
| cloudeye-exporter | br_release_sdk_v3 | main |
| cloudide-plugin-api | codearts | main |
| cloudide-plugin-core | codearts | main |
| generator-cloudide-plugin | codearts | main |
| dws_ai_native | dws_autopilot_mcp_server | main |
| huaweicloud-cloud-init | 0.7.9 | main |
| huaweicloud-lts-sdk-go | out.github | main |

**注意：** cloudeye-exporter (108★) 是热门仓库，分支变更需提前通知所有协作者

### 4.3 P0-6：单人维护仓库添加Backup（优先Top50）

从67个单人维护仓库中，优先处理Stars≥10的活跃仓库。

```bash
# 导出单人维护仓库清单
gh api "orgs/huaweicloud/repos?type=all&per_page=100&page=1" --jq '.[] | select(.archived==false) | "\(.name) \(.stargazers_count)"' > /tmp/repos.txt
# 交叉对比contributors数据，筛选单人维护+Stars≥10的仓库
```

---

## 五、W3 — 筑基（D15-D21）

### 目标：补全社区准入门槛文件 + 模板体系

### 5.1 P1-1：Stars≥50 仓库社区文件补全（17个仓库）

| 仓库 | Stars | CONTRIBUTING | SECURITY | CoC | Issue模板 | PR模板 |
|------|-------|:---:|:---:|:---:|:---:|:---:|
| ModelArts-Lab | 1040 | ❌ | ❌ | ❌ | ❌ | ❌ |
| spring-cloud-huawei | 576 | ❌ | ❌ | ❌ | ❌ | ❌ |
| terraform-provider-huaweicloud | 271 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-mrs-example | 239 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-sdk-python-v3 | 160 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-sdk-java-obs | 152 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-sdk-java-v3 | 138 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-sdk-go-v3 | 129 | ❌ | ❌ | ❌ | ❌ | ❌ |
| cloudeye-exporter | 108 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-sdk-python-obs | 87 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-iot-device-sdk-c | 85 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-sdk-cpp-v3 | 65 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-iot-device-sdk-java | 63 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-fpga | 57 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-sdk-c-obs | 57 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-sdk-php-obs | 57 | ❌ | ❌ | ❌ | ❌ | ❌ |
| huaweicloud-sdk-go-obs | 54 | ❌ | ❌ | ❌ | ❌ | ❌ |

**文件模板（已准备在`../../github-templates/`）：**
- CONTRIBUTING.md — 贡献流程、开发环境搭建、PR规范
- SECURITY.md — 安全漏洞报告流程（mailto渠道）
- CODE_OF_CONDUCT.md — 贡献者行为准则
- .github/ISSUE_TEMPLATE/bug_report.yml — Bug报告表单
- .github/ISSUE_TEMPLATE/feature_request.yml — 功能请求表单
- .github/PULL_REQUEST_TEMPLATE.md — PR模板

### 5.2 P1-2：Stars≥50仓库启用Dependabot

```bash
# 创建 .github/dependabot.yml
for repo in ModelArts-Lab spring-cloud-huawei terraform-provider-huaweicloud huaweicloud-mrs-example huaweicloud-sdk-python-v3 huaweicloud-sdk-java-obs huaweicloud-sdk-java-v3 huaweicloud-sdk-go-v3 cloudeye-exporter huaweicloud-sdk-python-obs huaweicloud-iot-device-sdk-c huaweicloud-sdk-cpp-v3 huaweicloud-iot-device-sdk-java huaweicloud-fpga huaweicloud-sdk-c-obs huaweicloud-sdk-php-obs huaweicloud-sdk-go-obs; do
  gh api -X PUT "repos/huaweicloud/$repo/contents/.github/dependabot.yml" \
    -f message="ci: enable Dependabot security updates" \
    -f content="$(cat <<'YAML' | base64 -w0
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "maven"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "gomod"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
YAML
)"
  echo "✓ $repo Dependabot配置已添加"
done
```

---

## 六、W4 — 筑基 + 收尾（D22-D30）

### 目标：安全扫描 + 自动巡检 + 月度报告

### 6.1 P1-3：Stars≥50仓库启用CodeQL

```yaml
# .github/workflows/codeql.yml
name: "CodeQL"
on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
  schedule:
    - cron: '30 1 * * 0'

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
    - uses: actions/checkout@v4
    - uses: github/codeql-action/init@v3
    - uses: github/codeql-action/analyze@v3
```

按语言分别配置（Go/Java/Python/TypeScript）。

### 6.2 P1-4：自动化月度巡检脚本

创建定时巡检 workflow（每月1日），检查项：

```bash
# 巡检项（.github/workflows/governance-audit.yml）
1. License覆盖率 — 通过GitHub API检查LICENSE文件
2. 单人维护仓库数 — 交叉对比collaborators API
3. 分支保护覆盖率 — 检查protection API
4. 社区文件覆盖率 — 检查CONTRIBUTING/SECURITY/CoC
5. 非标准分支名 — 检查default_branch
6. Issues禁用 — 检查has_issues
7. 安全告警数 — 检查Dependabot alerts API
```

**输出：** 月度治理报告Issue（自动创建 + @mention异常项责任人）

### 6.3 月度报告

```
8月整改月度报告模板
├── 执行概览（完成率）
├── 各维度前后对比
│   ├── License: 80% → 100%
│   ├── 分支保护: 15.5% → ≥24.5%
│   ├── 单人维护: 67 → ≤10
│   ├── 社区文件: 2-4% → Stars≥50仓库100%
│   └── 安全扫描: 2.6% → Stars≥50仓库100%
├── 未达标项与阻塞
├── 9月计划预告
└── 风险清单更新
```

---

## 七、责任矩阵

| 角色 | 职责 | 覆盖范围 |
|------|------|----------|
| 组织管理员(hermes助手) | 批量脚本执行、进度追踪 | 全组织155仓库 |
| SDK团队负责人 | SDK仓库License/Label/CI | ~30个SDK仓库 |
| 安全团队 | Critical告警修复、安全策略 | 全组织 |
| OSPO/开源办公室 | 社区文件模板、CLA体系 | 全组织 |
| 各Repo Owner | 分支保护确认、Issue/PR模板合并 | Stars≥50仓库 |

---

## 八、里程碑与检查点

| 日期 | 里程碑 | 验收方式 |
|------|--------|----------|
| D2 | huaweicloud/.github 仓库上线 | 仓库存在 + 13个文件就位 |
| D7 (W1末) | License 100% + Issues 100%启用 | `gh api` 逐一验证 |
| D14 (W2末) | Stars≥20仓库分支保护100% + 分支名统一100% | protection API + 分支检查 |
| D21 (W3末) | Stars≥50仓库社区文件100% + Dependabot 100% | 文件存在性检查 |
| D30 (W4末) | CodeQL 100% + 巡检脚本上线 + 月度报告 | CodeQL workflow存在 + 测试巡检运行 |

---

## 九、风险与应对

| 风险 | 可能性 | 应对 |
|------|--------|------|
| 仓库Owner不响应PR | 高 | 48h后自动升级到团队负责人→组织管理员 |
| Free plan私有仓库无法设分支保护 | 中 | 仅配置public仓库，私有仓库改为文档要求 |
| cloudeye-exporter分支名变更影响用户 | 中 | 提前1周通知+GitHub默认分支切换工具 |
| 批量脚本token速率限制 | 低 | 控制并发，添加sleep间隔 |
| 社区文件模板不符合团队规范 | 低 | 模板为通用版本，各团队可后续定制 |

---

## 十、脚本与工具

所有自动化脚本存放位置：
```
/home/zhangshuang/github-community-governance/月度计划/scripts/
├── add_license.sh          # 批量添加LICENSE
├── enable_issues.sh        # 批量启用Issues
├── set_branch_protection.sh # 批量设置分支保护
├── normalize_branches.sh   # 分支名统一
├── add_community_files.sh  # 批量添加社区文件
├── enable_dependabot.sh    # 批量启用Dependabot
├── enable_codeql.sh        # 批量启用CodeQL
└── governance_audit.sh     # 月度巡检脚本
```

---

*数据核验：基于2026-07-24盘点数据，关键数字已通过`repos-basic.json` + `branch-release.json` + `contributors.json`二次核验修正*
*编制工具：Hermes Agent*
