#!/usr/bin/env bash
# End-to-end demo: generate the synthetic sheets, validate all three
# bundled datasets, and run the unit tests.
#
# The validator core is standard-library only; the venv python is used
# when present (it also serves the optional API), otherwise system
# python3. Exit code 0 overall: the bad-sheet validation is EXPECTED
# to report errors, so its non-zero validator exit code is captured,
# not fatal.
set -u
cd "$(dirname "$0")"

if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
else
  PY=python3
fi

echo "=== 1. Generate synthetic sample sheets (labeled synthetic) ==="
$PY data/generate_synthetic.py
echo

echo "=== 2. Validate the CLEAN synthetic sample sheet (expect 0 errors) ==="
$PY -m src.cli validate \
  --input data/synthetic_sample_sheet.csv \
  --schema data/sample_sheet_schema.json \
  --vocab data/vocabularies.json \
  --metadata data/sample_sheet_metadata.json \
  --out reports/sample_sheet_clean_report.json \
  --summary reports/sample_sheet_clean_summary.md \
  --synthetic
echo "validator exit code: $?"
echo

echo "=== 3. Validate the SEEDED-DEFECT synthetic sheet (expect errors) ==="
$PY -m src.cli validate \
  --input data/synthetic_sample_sheet_bad.csv \
  --schema data/sample_sheet_schema.json \
  --vocab data/vocabularies.json \
  --metadata data/sample_sheet_metadata_bad.json \
  --out reports/sample_sheet_bad_report.json \
  --summary reports/sample_sheet_bad_summary.md \
  --synthetic || echo "validator exit code: $? (expected: defects found)"
echo

echo "=== 4. Validate the REAL public dataset (UCI Iris, CC BY 4.0) ==="
$PY -m src.cli validate \
  --input data/iris.csv \
  --schema data/iris_schema.json \
  --vocab data/vocabularies.json \
  --metadata data/iris_metadata.json \
  --out reports/iris_report.json \
  --summary reports/iris_summary.md \
  --license "CC BY 4.0 (UCI Machine Learning Repository)"
echo "validator exit code: $?"
echo

echo "=== 5. Unit tests ==="
$PY -m unittest discover -s tests -v
echo
echo "Reports written to reports/ (JSON + Markdown summaries)."
