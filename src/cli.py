"""Command-line entry point for dataset-curation-qa.

Usage (from the project root):

    python3 -m src.cli validate --input data/synthetic_sample_sheet.csv \\
        --schema data/sample_sheet_schema.json \\
        --vocab data/vocabularies.json \\
        --metadata data/sample_sheet_metadata.json \\
        --out reports/sample_sheet_report.json \\
        --summary reports/sample_sheet_summary.md \\
        --synthetic

Exit code 0 means no errors were found (warnings/info flags are OK);
exit code 1 means at least one error was found.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.report import write_json_report, write_summary
from src.validator import load_json, validate_dataset


def cmd_validate(args):
    raw = Path(args.input).read_bytes()
    schema = load_json(args.schema)
    vocabularies = load_json(args.vocab) if args.vocab else {}
    metadata = load_json(args.metadata) if args.metadata else {}

    report = validate_dataset(
        raw,
        schema,
        vocabularies=vocabularies,
        metadata=metadata,
        source_name=Path(args.input).name,
        synthetic=args.synthetic,
        license_text=args.license,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_report(report, out_path)
    if args.summary:
        summary_path = Path(args.summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        write_summary(report, summary_path)

    summary = report["summary"]
    print(f"rows checked: {report['data_provenance']['rows_checked']}")
    print(f"checks run: {len(report['checks_run'])}")
    print(
        f"issues: {summary['total_issues']} total, "
        f"{summary['errors']} errors, {summary['warnings']} warnings, "
        f"{summary['info']} info"
    )
    print(f"report: {out_path}")
    if args.summary:
        print(f"summary: {args.summary}")
    return 1 if summary["errors"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="dataset-curation-qa",
        description="Validate a tabular research dataset + metadata "
        "against a FAIR-inspired checklist.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate one CSV dataset")
    validate.add_argument("--input", required=True, help="CSV file to validate")
    validate.add_argument("--schema", required=True, help="schema JSON file")
    validate.add_argument("--vocab", help="controlled-vocabulary JSON file")
    validate.add_argument("--metadata", help="dataset-level metadata JSON file")
    validate.add_argument("--out", required=True, help="JSON report output path")
    validate.add_argument("--summary", help="Markdown summary output path")
    validate.add_argument("--synthetic", action="store_true",
                          help="mark the input data as synthetic in the report")
    validate.add_argument("--license", default="",
                          help="license / provenance note recorded in the report")
    validate.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
