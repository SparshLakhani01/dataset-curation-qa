"""Dataset Curation & QA validator.

Validates a tabular research dataset (CSV) plus its dataset-level
metadata against a FAIR-inspired checklist:

  * schema conformance (expected columns, value types, patterns)
  * required-field completeness (per-row and dataset-level metadata)
  * controlled-vocabulary checks (values against an allow-list)
  * missingness statistics per column
  * duplicate primary keys and duplicate rows
  * numeric range checks
  * IQR-based outlier flags (statistical flags, not defects)
  * referenced-file existence checks

Every report carries a provenance block: source file name, SHA-256
checksum of the validated bytes, validation timestamp, tool version,
and schema name/version.

Standard library only. No network access, no external services, no
Synapse integration, no clinical or genomic interpretation: this tool
checks the shape and consistency of a dataset, not the science in it.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

TOOL_NAME = "dataset-curation-qa"
TOOL_VERSION = "0.1.0"

MISSINGNESS_WARNING_RATE = 0.20
OUTLIER_IQR_MULTIPLIER = 1.5
MIN_VALUES_FOR_OUTLIER_CHECK = 8


class Issue:
    """One validation finding."""

    def __init__(self, category, severity, message, row=None, column=None):
        self.category = category
        self.severity = severity  # "error", "warning", or "info"
        self.message = message
        self.row = row  # 1-based data-row number (header excluded), or None
        self.column = column

    def to_dict(self):
        return {
            "category": self.category,
            "severity": self.severity,
            "row": self.row,
            "column": self.column,
            "message": self.message,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_empty(value):
    return value is None or str(value).strip() == ""


def _parse_typed(value, col_type):
    """Return (ok, parsed_value). Strings always parse."""
    text = str(value).strip()
    if col_type == "string":
        return True, text
    if col_type == "integer":
        try:
            return True, int(text)
        except ValueError:
            return False, None
    if col_type == "number":
        try:
            parsed = float(text)
        except ValueError:
            return False, None
        if math.isnan(parsed) or math.isinf(parsed):
            return False, None
        return True, parsed
    if col_type == "date":
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return False, None
        return True, text
    if col_type == "boolean":
        if text.lower() in ("true", "false", "yes", "no", "1", "0"):
            return True, text.lower() in ("true", "yes", "1")
        return False, None
    return False, None


def _quartiles(sorted_values):
    """Tukey-style quartiles via linear interpolation (no numpy)."""
    n = len(sorted_values)

    def percentile(p):
        rank = p * (n - 1)
        low = int(rank)
        high = min(low + 1, n - 1)
        frac = rank - low
        return sorted_values[low] * (1 - frac) + sorted_values[high] * frac

    return percentile(0.25), percentile(0.75)


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv_rows(raw_bytes, schema):
    """Return (rows, header_present, parse_issues).

    rows is a list of dicts keyed by column name. When the schema says
    header=false, column names come from the schema itself.
    """
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    all_lines = [line for line in reader if line]
    issues = []
    column_names = [c["name"] for c in schema["columns"]]

    if schema.get("header", True):
        if not all_lines:
            return [], True, [Issue("schema", "error", "CSV file is empty")]
        header = [h.strip() for h in all_lines[0]]
        data_lines = all_lines[1:]
        rows = []
        for idx, line in enumerate(data_lines, start=1):
            row = {}
            for pos, name in enumerate(header):
                row[name] = line[pos] if pos < len(line) else ""
            if len(line) > len(header):
                issues.append(
                    Issue(
                        "schema",
                        "error",
                        f"Row has {len(line)} fields but header has "
                        f"{len(header)}",
                        row=idx,
                    )
                )
            rows.append(row)
        return rows, header, issues

    rows = []
    for idx, line in enumerate(all_lines, start=1):
        if len(line) != len(column_names):
            issues.append(
                Issue(
                    "schema",
                    "error",
                    f"Row has {len(line)} fields but schema declares "
                    f"{len(column_names)}",
                    row=idx,
                )
            )
        row = {}
        for pos, name in enumerate(column_names):
            row[name] = line[pos] if pos < len(line) else ""
        rows.append(row)
    return rows, None, issues


def validate_dataset(raw_bytes, schema, vocabularies=None, metadata=None,
                     source_name="", synthetic=False, license_text=""):
    """Run every check and return the full report dict."""
    vocabularies = vocabularies or {}
    metadata = metadata or {}
    issues = []
    checks_run = []

    rows, header, parse_issues = read_csv_rows(raw_bytes, schema)
    issues.extend(parse_issues)

    columns = {c["name"]: c for c in schema["columns"]}
    declared = [c["name"] for c in schema["columns"]]

    # 1. Schema conformance: expected columns present / unexpected absent.
    checks_run.append("schema_conformance")
    if header is not None:
        for name in declared:
            if name not in header:
                issues.append(
                    Issue("schema", "error",
                          f"Expected column '{name}' is missing from the header")
                )
        for name in header:
            if name not in columns:
                issues.append(
                    Issue("schema", "warning",
                          f"Unexpected column '{name}' is not in the schema")
                )

    # Per-column value checks: types, patterns, required, vocabulary, range.
    typed_values = {name: {} for name in declared}  # name -> row -> parsed
    for col in schema["columns"]:
        name = col["name"]
        for idx, row in enumerate(rows, start=1):
            value = row.get(name, "")
            if _is_empty(value):
                if col.get("required"):
                    issues.append(
                        Issue("required_field", "error",
                              f"Required field '{name}' is empty",
                              row=idx, column=name)
                    )
                continue
            ok, parsed = _parse_typed(value, col.get("type", "string"))
            if not ok:
                issues.append(
                    Issue("schema", "error",
                          f"Value '{value}' is not a valid "
                          f"{col.get('type', 'string')}",
                          row=idx, column=name)
                )
                continue
            typed_values[name][idx] = parsed
            pattern = col.get("pattern")
            if pattern and not re.fullmatch(pattern, str(value).strip()):
                issues.append(
                    Issue("schema", "error",
                          f"Value '{value}' does not match pattern '{pattern}'",
                          row=idx, column=name)
                )
            vocab_name = col.get("vocabulary")
            if vocab_name:
                allowed = vocabularies.get(vocab_name, [])
                if str(value).strip() not in allowed:
                    issues.append(
                        Issue("controlled_vocabulary", "error",
                              f"Value '{value}' is not in the '{vocab_name}' "
                              f"controlled vocabulary {sorted(allowed)}",
                              row=idx, column=name)
                    )
            if col.get("type") in ("integer", "number"):
                if "min" in col and parsed < col["min"]:
                    issues.append(
                        Issue("range", "error",
                              f"Value {parsed} is below minimum {col['min']}",
                              row=idx, column=name)
                    )
                if "max" in col and parsed > col["max"]:
                    issues.append(
                        Issue("range", "error",
                              f"Value {parsed} exceeds maximum {col['max']}",
                              row=idx, column=name)
                    )
    checks_run.append("required_fields")
    checks_run.append("controlled_vocabulary")
    checks_run.append("range")

    # 2. Dataset-level metadata completeness.
    checks_run.append("metadata_completeness")
    for field in schema.get("required_metadata", []):
        if field not in metadata or _is_empty(metadata.get(field)):
            issues.append(
                Issue("metadata", "error",
                      f"Required dataset metadata field '{field}' is "
                      "missing or empty")
            )

    # 3. Missingness statistics per column.
    checks_run.append("missingness")
    column_stats = []
    for name in declared:
        missing = sum(1 for row in rows if _is_empty(row.get(name, "")))
        rate = (missing / len(rows)) if rows else 0.0
        column_stats.append({
            "column": name,
            "non_missing": len(rows) - missing,
            "missing": missing,
            "missing_rate": round(rate, 4),
        })
        if rows and rate > MISSINGNESS_WARNING_RATE:
            issues.append(
                Issue("missingness", "warning",
                      f"Column '{name}' is {rate:.1%} missing "
                      f"({missing}/{len(rows)} rows)",
                      column=name)
            )

    # 4. Duplicates: primary keys and full rows.
    checks_run.append("duplicates")
    pk_fields = schema.get("primary_key", [])
    if pk_fields:
        seen = {}
        for idx, row in enumerate(rows, start=1):
            key = tuple(str(row.get(f, "")).strip() for f in pk_fields)
            if all(_is_empty(v) for v in key):
                continue
            if key in seen:
                issues.append(
                    Issue("duplicates", "error",
                          f"Duplicate primary key {key} (first seen in "
                          f"row {seen[key]})",
                          row=idx, column=",".join(pk_fields))
                )
            else:
                seen[key] = idx
    seen_rows = {}
    for idx, row in enumerate(rows, start=1):
        key = tuple(str(row.get(name, "")).strip() for name in declared)
        if key in seen_rows:
            issues.append(
                Issue("duplicates", "warning",
                      f"Row is an exact duplicate of row {seen_rows[key]}",
                      row=idx)
            )
        else:
            seen_rows[key] = idx

    # 5. IQR outlier flags on numeric columns (informational only).
    checks_run.append("outliers")
    for col in schema["columns"]:
        if col.get("type") not in ("integer", "number"):
            continue
        values = sorted(typed_values[col["name"]].values())
        if len(values) < MIN_VALUES_FOR_OUTLIER_CHECK:
            continue
        q1, q3 = _quartiles(values)
        iqr = q3 - q1
        low = q1 - OUTLIER_IQR_MULTIPLIER * iqr
        high = q3 + OUTLIER_IQR_MULTIPLIER * iqr
        for idx, parsed in typed_values[col["name"]].items():
            if parsed < low or parsed > high:
                issues.append(
                    Issue("outlier", "info",
                          f"Value {parsed} lies outside the IQR fence "
                          f"[{low:.3g}, {high:.3g}] for column "
                          f"'{col['name']}' (statistical flag, not a defect)",
                          row=idx, column=col["name"])
                )

    # 6. Referenced-file existence.
    checks_run.append("file_references")
    for col in schema["columns"]:
        if not col.get("must_exist"):
            continue
        base = Path(col.get("base_dir", ".")).resolve()
        for idx, row in enumerate(rows, start=1):
            value = str(row.get(col["name"], "")).strip()
            if _is_empty(value):
                continue
            candidate = (base / value).resolve()
            try:
                candidate.relative_to(base)
            except ValueError:
                issues.append(
                    Issue("file_reference", "error",
                          f"Referenced path '{value}' escapes the base "
                          f"directory '{base}'",
                          row=idx, column=col["name"])
                )
                continue
            if not candidate.exists():
                issues.append(
                    Issue("file_reference", "error",
                          f"Referenced file '{value}' does not exist under "
                          f"'{base}'",
                          row=idx, column=col["name"])
                )

    issues.sort(key=lambda i: (i.category, i.row or 0, i.column or ""))

    by_category = {}
    by_severity = {"error": 0, "warning": 0, "info": 0}
    for issue in issues:
        by_category[issue.category] = by_category.get(issue.category, 0) + 1
        by_severity[issue.severity] += 1

    return {
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_provenance": {
            "source_file": source_name,
            "sha256": sha256_bytes(raw_bytes),
            "bytes": len(raw_bytes),
            "rows_checked": len(rows),
            "synthetic": synthetic,
            "license": license_text,
        },
        "schema": {
            "name": schema.get("schema_name", "unnamed"),
            "version": schema.get("schema_version", "unknown"),
        },
        "checks_run": checks_run,
        "summary": {
            "total_issues": len(issues),
            "errors": by_severity["error"],
            "warnings": by_severity["warning"],
            "info": by_severity["info"],
            "by_category": by_category,
        },
        "column_stats": column_stats,
        "issues": [i.to_dict() for i in issues],
    }
