"""Generate the SYNTHETIC demo sample sheets for dataset-curation-qa.

SYNTHETIC DATA: every sample ID, donor ID, age, tissue, assay, and
file path in the generated CSVs is invented by this script with a
fixed random seed. There are no real donors, no real samples, and no
real sequencing files. The referenced files under data/files/ are
empty placeholder files created only so the file-existence check has
something to resolve; they contain no sequence data.

Two sheets are written:

* synthetic_sample_sheet.csv — 40 clean rows. Every row passes every
  check. Used to show the validator accepts well-formed data.
* synthetic_sample_sheet_bad.csv — 40 rows with 10 seeded defects
  (row numbers are 1-based data rows, header excluded):

    row  5: tissue empty (missing required field)
    row  9: assay "Proteomics" (out-of-vocabulary value)
    row 12: sample_id duplicated from row 3 (duplicate primary key)
    row 15: donor_age 250 (out of range 0-110)
    row 18: collection_date "15/03/2025" (wrong date format)
    row 21: sample_id "SMP-ABC" (pattern violation)
    row 24: file_path references SMP-9999_R1.fastq.gz (missing file)
    row 27: donor_sex "F" (out-of-vocabulary value)
    row 30: donor_id empty (missing required field)
    row 33: donor_age "thirty" (type error)
    row 40: exact copy of row 2 (duplicate row + duplicate primary key)

  The validator is expected to flag all of these; the unit tests assert
  the three headline categories (missing field, out-of-vocabulary,
  duplicate key) directly.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FILES = DATA / "files"

TISSUES = ["blood", "tumor", "normal adjacent tissue", "cell line"]
ASSAYS = ["RNA-seq", "WES", "WGS", "ATAC-seq"]
SEXES = ["female", "male", "unknown"]

HEADER = [
    "sample_id",
    "donor_id",
    "tissue",
    "assay",
    "donor_age",
    "donor_sex",
    "file_path",
    "collection_date",
]


def build_clean_rows(rng, count=40):
    rows = []
    for i in range(1, count + 1):
        sample_id = f"SMP-{i:04d}"
        rows.append({
            "sample_id": sample_id,
            "donor_id": f"DON-{rng.randint(100, 199)}",
            "tissue": rng.choice(TISSUES),
            "assay": rng.choice(ASSAYS),
            "donor_age": str(rng.randint(18, 89)),
            "donor_sex": rng.choice(SEXES),
            "file_path": f"{sample_id}_R1.fastq.gz",
            "collection_date": f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
        })
    return rows


def seed_defects(rows):
    """Mutate a copy of the clean rows with the documented defects."""
    bad = [dict(r) for r in rows]
    bad[4]["tissue"] = ""                       # row 5
    bad[8]["assay"] = "Proteomics"              # row 9
    bad[11]["sample_id"] = bad[2]["sample_id"]  # row 12 duplicates row 3
    bad[14]["donor_age"] = "250"                # row 15
    bad[17]["collection_date"] = "15/03/2025"   # row 18
    bad[20]["sample_id"] = "SMP-ABC"            # row 21
    bad[23]["file_path"] = "SMP-9999_R1.fastq.gz"  # row 24
    bad[26]["donor_sex"] = "F"                  # row 27
    bad[29]["donor_id"] = ""                    # row 30
    bad[32]["donor_age"] = "thirty"             # row 33
    bad[39] = dict(bad[1])                      # row 40 duplicates row 2
    return bad


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)


def create_placeholders(rows_list):
    """Create empty placeholder files for every referenced path except
    the intentionally missing SMP-9999 file."""
    FILES.mkdir(parents=True, exist_ok=True)
    created = 0
    for rows in rows_list:
        for row in rows:
            name = row["file_path"]
            if name == "SMP-9999_R1.fastq.gz":
                continue
            target = FILES / name
            if not target.exists():
                target.write_bytes(b"")
                created += 1
    return created


def main():
    rng = random.Random(20261116)
    clean = build_clean_rows(rng)
    bad = seed_defects(clean)
    write_csv(DATA / "synthetic_sample_sheet.csv", clean)
    write_csv(DATA / "synthetic_sample_sheet_bad.csv", bad)
    created = create_placeholders([clean, bad])
    print(f"wrote {DATA / 'synthetic_sample_sheet.csv'} ({len(clean)} rows, clean)")
    print(f"wrote {DATA / 'synthetic_sample_sheet_bad.csv'} ({len(bad)} rows, 10 seeded defects)")
    print(f"placeholder files under data/files/: {created} created")


if __name__ == "__main__":
    main()
