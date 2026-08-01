<!--
  月报模板 - 由 stats_report.py 渲染后通过邮件发送
  此模板仅作为参考，实际内容由脚本动态生成
-->
## huaweicloud-mate Issues 月报

| 项目 | 值 |
|------|-----|
| 周期 | {year}-{month} |
| 生成时间 | {generated_at} |

### 概览

| 指标 | 本月 | 变化 |
|------|------|------|
| 新建 Issue | {new_this_month} | {new_change} |
| 已关闭 | {closed} | {closed_change} |
| 活跃 (已开启) | {open_count} | {open_change} |
| 总 Issue 数 | {total} | - |

### 按类型分布

{type_table}

### SLA 达标率

- 总达标率：{sla_rate}%（目标 90%）
- critical：{sla_critical}%
- high：{sla_high}%
- medium：{sla_medium}%
- low：{sla_low}%

### 仓库 Issue 排行（TOP 10）

{repo_top10_table}

### GitCode 统计（hd-vector）

{gitcode_table}

### 团队贡献排行

{contributor_table}

### 月报总结

{summary}
