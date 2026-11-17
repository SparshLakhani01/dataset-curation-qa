# Dataset Curation & QA

A working prototype that validates a tabular research dataset plus its
dataset-level metadata against a FAIR-inspired checklist, and emits a
machine-readable quality report (JSON) with a provenance log plus a
short human-readable summary (Markdown). The checks mirror the kind of
stewardship work a research data portal needs: is the table shaped the
way its schema promises, is the required metadata present, do values
use the controlled vocabularies, and can every row be traced back to a
source file and checksum?

## Data disclosure — read this first

**Two datasets ship with this project, and they are different kinds of
data. The reports label each one.**

1. **Real public data:** `data/iris.csv` is the Iris flower dataset
   (R. A. Fisher, 1936), fetched unmodified from the UCI Machine
   Learning Repository (CC BY 4.0,
   https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data).
   150 rows, no header row in the source file. It is real, published
   data — not genomics data, and not presented as such. It exercises
   the validator on an independent, real-world table.
2. **Synthetic data:** `data/synthetic_sample_sheet*.csv` are
   clearly-labeled synthetic sample sheets modeled on a genomics
   sample sheet (sample IDs, donor IDs, tissue, assay, donor age/sex,
   file references, collection dates). Every value was invented by
   `data/generate_synthetic.py` with a fixed seed. There are no real
   donors, no real samples, and no real sequencing files: the files
   under `data/files/` are empty placeholders created only so the
   file-existence check has something to resolve. Synthetic inputs are
   labeled `synthetic: true` in the generator, in the filenames, and
   in every report's provenance block. **Never present the synthetic
   sheets as real research data.**

## What it does

Given a CSV, a schema spec (JSON), controlled vocabularies (JSON), and
dataset-level metadata (JSON), the validator runs 9 checks:

| # | Check | What it catches |
|---|-------|-----------------|
| 1 | Schema conformance | Missing/unexpected columns, wrong value types, pattern violations (e.g. sample-ID format) |
| 2 | Required fields | Empty required cells, per row |
| 3 | Controlled vocabulary | Values outside an allow-list (tissue, assay, sex, species) |
| 4 | Range | Numeric values outside declared min/max |
| 5 | Metadata completeness | Missing/empty required dataset-level fields (title, description, creator, license, version) |
| 6 | Missingness | Per-column missing counts/rates; warns above a 20% missing rate |
| 7 | Duplicates | Duplicate primary keys (error) and exact duplicate rows (warning) |
| 8 | Outliers | IQR-fence flags on numeric columns — informational only, explicitly "a statistical flag, not a defect" |
| 9 | File references | Referenced file paths must exist under a declared base directory; path-traversal attempts are rejected |

Every report carries a provenance block: source file name, SHA-256
checksum of the validated bytes, byte count, rows checked, validation
timestamp (UTC), tool version, schema name/version, a synthetic-data
flag, and a license note.

## Measured results

From `./demo.sh`, run on 2026-11-16 in this environment (full reports
in `reports/`):

| Dataset | Rows | Checks | Errors | Warnings | Info |
|---------|-----:|-------:|-------:|---------:|-----:|
| Clean synthetic sample sheet | 40 | 9 | 0 | 0 | 0 |
| Seeded-defect synthetic sheet | 40 | 9 | 13 | 1 | 1 |
| UCI Iris (real, CC BY 4.0) | 150 | 9 | 0 | 3 | 4 |

The seeded-defect sheet carries 10 deliberate defects (plus a
defective metadata file missing `creator` and `license`), and the
validator caught all of them — 13 errors across 6 categories:
2 missing required fields, 2 out-of-vocabulary values, 2 duplicate
primary keys, 1 range violation, 3 schema errors (bad date, bad ID
pattern, bad integer), 1 missing referenced file, and 2 missing
metadata fields — plus 1 duplicate-row warning and 1 IQR outlier flag
on the out-of-range age value.

On the real Iris data the validator found 0 errors and surfaced 3
genuine exact-duplicate rows (rows 35 and 38 duplicate row 10; row 143
duplicates row 102) and 4 IQR outlier flags on `sepal_width` — real
properties of that dataset, reported as warnings/info, not defects.

Unit tests: **10 tests, all passing** (`python3 -m unittest discover
-s tests -v`), including direct assertions that the validator catches
a missing required field, an out-of-vocabulary value, and a duplicate
primary key, plus a test that the defective demo sheet flags every
seeded-defect category.

The optional API was verified live: `GET /health` returned
`{"status": "ok", "tool_version": "0.1.0"}`, and `POST /validate` on
the defective sheet returned 40 rows checked, 10 errors, 12 issues
(the API skips on-disk file-existence checks and was given complete
metadata in that call, which accounts for the 3 fewer errors versus
the CLI run).

**Read these numbers with care:** the synthetic sheets are small
(40 rows), invented by the same author as the validator, and the
defects were planted to be found. The numbers show the mechanism
works on this data; they say nothing about performance on real,
messy portal submissions.

## How to run

The validator core and CLI are standard-library only — no install
needed. The optional API needs FastAPI + uvicorn.

```bash
# Everything in one go: generate, validate all three datasets, test
./demo.sh

# Or step by step
python3 data/generate_synthetic.py
python3 -m src.cli validate \
  --input data/synthetic_sample_sheet.csv \
  --schema data/sample_sheet_schema.json \
  --vocab data/vocabularies.json \
  --metadata data/sample_sheet_metadata.json \
  --out reports/sample_sheet_clean_report.json \
  --summary reports/sample_sheet_clean_summary.md \
  --synthetic
python3 -m unittest discover -s tests -v

# API (optional)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn api:app --port 8000
curl http://127.0.0.1:8000/health
```

The CLI exits 0 when no errors are found and 1 when at least one
error is found, so it can gate an ingest pipeline.

## Architecture

```
data/generate_synthetic.py  -> data/synthetic_sample_sheet*.csv, data/files/* (placeholders)
data/iris.csv               -> real public dataset, fetched unmodified (CC BY 4.0)
data/*_schema.json          -> column specs: types, required, patterns, ranges, vocabularies
data/vocabularies.json      -> controlled vocabularies (allow-lists)
data/*_metadata.json        -> dataset-level metadata under test
src/validator.py            -> all 9 checks + provenance block (stdlib only)
src/report.py               -> JSON report + Markdown summary writers
src/cli.py                  -> argparse CLI (exit 0/1 on errors)
api.py                      -> FastAPI: /health, /validate (optional)
tests/test_validator.py     -> 10 unit tests (stdlib unittest)
demo.sh                     -> end-to-end demo script
reports/                    -> generated JSON reports + Markdown summaries
```

## Honest limitations

- **No Synapse integration.** The NF Data Portal is built on Synapse;
  this tool does not talk to Synapse, its API, or any portal. It
  validates local CSV + JSON files only. Wiring it to a real portal
  (entity annotations, provenance chains, access controls) is future
  work, not done here.
- **FAIR-inspired, not FAIR-certified.** The checklist borrows FAIR
  ideas (findable metadata, accessible formats, interoperable
  vocabularies, reusable provenance) but this is not a FAIR
  assessment, certification, or compliance claim of any kind.
- **No ontology expertise.** Vocabularies here are flat allow-lists in
  a JSON file. There is no ontology lookup, term resolution, or
  hierarchy handling (no OBO, OWL, or BioPortal use).
- **No clinical or genomic interpretation.** The tool checks the
  shape and consistency of a table. It knows nothing about what the
  values mean biologically, and no result here should be read as a
  scientific finding.
- **No real genomics data was used.** The genomics-flavored inputs
  are synthetic; the only real dataset is Iris flower measurements.
- **Exact-match vocabularies.** Values must match the allow-list
  exactly (case-sensitive). Real curation needs fuzzy matching,
  synonym mapping, and curator review — none of that is here.
- **Outlier flags are naive.** A single IQR fence per numeric column.
  Real data has legitimate skew, batches, and subgroups; flags are
  informational and need a human curator.
- **Single-file, in-memory.** One CSV at a time, loaded fully into
  memory. No streaming, no database, no incremental validation.
- **No auth or permissions model.** The API has none; do not expose
  it beyond localhost.
- **Small, self-authored tests.** 10 tests against data the author
  also wrote. Directional only.

## Files

| File | Purpose |
|------|---------|
| `src/validator.py` | 9 validation checks + provenance block |
| `src/report.py` | JSON report + Markdown summary writers |
| `src/cli.py` | Command-line entry point |
| `api.py` | Optional FastAPI service (`/health`, `/validate`) |
| `data/generate_synthetic.py` | Synthetic sheet generator (seeded, labeled) |
| `data/synthetic_sample_sheet.csv` | 40-row clean synthetic sheet (generated) |
| `data/synthetic_sample_sheet_bad.csv` | 40-row synthetic sheet, 10 seeded defects (generated) |
| `data/iris.csv` | Real UCI Iris data, fetched unmodified (CC BY 4.0) |
| `data/*_schema.json` | Schema specs for both datasets |
| `data/vocabularies.json` | Controlled vocabularies |
| `data/*_metadata.json` | Dataset-level metadata (incl. defective variant) |
| `data/files/` | Empty placeholder files for file-reference checks |
| `tests/test_validator.py` | 10 unit tests |
| `demo.sh` | End-to-end demo script |
| `requirements.txt` | API-only dependencies (FastAPI + uvicorn) |
| `reports/` | Generated reports from the verified demo run |
