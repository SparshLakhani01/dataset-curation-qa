"""Report writers: machine-readable JSON and a short human summary."""

from __future__ import annotations

import json

MAX_ISSUES_IN_SUMMARY = 25


def write_json_report(report, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")


def render_summary(report):
    """Render a short Markdown summary of a validation report."""
    prov = report["data_provenance"]
    summary = report["summary"]
    lines = [
        f"# Quality report: {prov['source_file']}",
        "",
        f"- Tool: {report['tool']} v{report['tool_version']}",
        f"- Generated (UTC): {report['generated_at_utc']}",
        f"- Rows checked: {prov['rows_checked']}",
        f"- SHA-256: `{prov['sha256']}`",
        f"- Synthetic data: {'yes' if prov['synthetic'] else 'no'}",
    ]
    if prov.get("license"):
        lines.append(f"- License: {prov['license']}")
    lines += [
        f"- Schema: {report['schema']['name']} v{report['schema']['version']}",
        f"- Checks run: {len(report['checks_run'])} "
        f"({', '.join(report['checks_run'])})",
        "",
        "## Result",
        "",
        f"{summary['total_issues']} issue(s): {summary['errors']} error(s), "
        f"{summary['warnings']} warning(s), {summary['info']} info flag(s).",
        "",
    ]
    if summary["by_category"]:
        lines.append("## Issues by category")
        lines.append("")
        for category, count in sorted(summary["by_category"].items()):
            lines.append(f"- {category}: {count}")
        lines.append("")
    lines.append("## Column missingness")
    lines.append("")
    lines.append("| column | non-missing | missing | missing rate |")
    lines.append("|---|---|---|---|")
    for stat in report["column_stats"]:
        lines.append(
            f"| {stat['column']} | {stat['non_missing']} | {stat['missing']} "
            f"| {stat['missing_rate']:.1%} |"
        )
    lines.append("")
    issues = report["issues"]
    if issues:
        lines.append(f"## Issues (showing {min(len(issues), MAX_ISSUES_IN_SUMMARY)} "
                     f"of {len(issues)})")
        lines.append("")
        for issue in issues[:MAX_ISSUES_IN_SUMMARY]:
            where = ""
            if issue["row"] is not None:
                where += f"row {issue['row']}"
            if issue["column"]:
                where += f" {issue['column']}" if where else issue["column"]
            lines.append(
                f"- [{issue['severity']}] {issue['category']}"
                + (f" ({where})" if where else "")
                + f": {issue['message']}"
            )
        lines.append("")
    return "\n".join(lines)


def write_summary(report, path):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_summary(report))
