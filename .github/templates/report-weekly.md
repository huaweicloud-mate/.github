<!--
  周报模板 - 由 stats_report.py 渲染后通过邮件发送
  此模板仅作为参考，实际内容由脚本动态生成
-->
## huaweicloud-mate Issues 周报

| 项目 | 值 |
|------|-----|
| 周期 | {year}-W{week} |
| 生成时间 | {generated_at} |

### 概览

| 指标 | 本周 | 变化 |
|------|------|------|
| 新建 Issue | {new_this_week} | {new_change} |
| 已关闭 | {closed_this_week} | {closed_change} |
| 活跃 | {open_count} | {open_change} |

### Issue 类型分布

{type_table}

### SLA 达标率

- 总达标率：{sla_rate}%（目标 90%）

{priority_sla_breakdown}

### GitCode 统计（hd-vector）

| 仓库 | 开启 | 关闭 | 合计 |
|------|------|------|------|

{gitcode_table}

### 仓库明细

{repo_table}

### 重点关注

{focus_items}
