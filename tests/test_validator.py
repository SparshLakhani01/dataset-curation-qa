"""Unit tests for the dataset-curation-qa validator.

Run from the project root:  python3 -m unittest discover -s tests -v

The three headline tests assert the validator catches known-bad
inputs: a missing required field, an out-of-vocabulary value, and a
duplicate primary key. The remaining tests cover the clean-sheet pass,
range/type errors, metadata completeness, file references, and the
provenance block.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from src.validator import load_json, validate_dataset

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

HEADER = "sample_id,donor_id,tissue,assay,donor_age,donor_sex,file_path,collection_date"


def make_csv(rows):
    return ("\n".join([HEADER] + [",".join(r) for r in rows]) + "\n").encode()


GOOD_ROW = ["SMP-0001", "DON-101", "blood", "RNA-seq", "45", "female",
            "SMP-0001_R1.fastq.gz", "2025-03-10"]
GOOD_ROW_2 = ["SMP-0002", "DON-102", "tumor", "WES", "61", "male",
              "SMP-0002_R1.fastq.gz", "2025-04-02"]


class ValidatorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_json(DATA / "sample_sheet_schema.json")
        cls.vocab = load_json(DATA / "vocabularies.json")
        cls.metadata = load_json(DATA / "sample_sheet_metadata.json")
        # File-existence checks resolve under data/files relative to the
        # working directory; tests run from the project root.
        cls.schema_no_files = json.loads(json.dumps(cls.schema))
        for col in cls.schema_no_files["columns"]:
            col.pop("must_exist", None)

    def validate(self, raw, schema=None, metadata=None):
        return validate_dataset(
            raw,
            schema or self.schema_no_files,
            vocabularies=self.vocab,
            metadata=self.metadata if metadata is None else metadata,
            source_name="test.csv",
            synthetic=True,
        )

    def categories(self, report):
        return [i["category"] for i in report["issues"]]

    def test_missing_required_field_is_caught(self):
        row = list(GOOD_ROW)
        row[2] = ""  # tissue empty
        report = self.validate(make_csv([row]))
        self.assertIn("required_field", self.categories(report))
        self.assertGreater(report["summary"]["errors"], 0)

    def test_out_of_vocabulary_value_is_caught(self):
        row = list(GOOD_ROW)
        row[3] = "Proteomics"  # not in the assay allow-list
        report = self.validate(make_csv([row]))
        hits = [i for i in report["issues"]
                if i["category"] == "controlled_vocabulary"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["column"], "assay")

    def test_duplicate_primary_key_is_caught(self):
        report = self.validate(make_csv([GOOD_ROW, list(GOOD_ROW)]))
        hits = [i for i in report["issues"]
                if i["category"] == "duplicates"
                and "primary key" in i["message"]]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["row"], 2)

    def test_clean_rows_pass_with_zero_errors(self):
        report = self.validate(make_csv([GOOD_ROW, GOOD_ROW_2]))
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["data_provenance"]["rows_checked"], 2)

    def test_range_violation_is_caught(self):
        row = list(GOOD_ROW)
        row[4] = "250"  # donor_age max is 110
        report = self.validate(make_csv([row]))
        self.assertIn("range", self.categories(report))

    def test_type_error_is_caught(self):
        row = list(GOOD_ROW)
        row[4] = "thirty"
        report = self.validate(make_csv([row]))
        hits = [i for i in report["issues"]
                if i["category"] == "schema" and i["column"] == "donor_age"]
        self.assertEqual(len(hits), 1)

    def test_missing_metadata_fields_are_caught(self):
        report = self.validate(make_csv([GOOD_ROW]),
                               metadata={"title": "x", "description": "y",
                                         "version": "1.0.0"})
        missing = {i["message"] for i in report["issues"]
                   if i["category"] == "metadata"}
        self.assertTrue(any("creator" in m for m in missing))
        self.assertTrue(any("license" in m for m in missing))

    def test_missing_referenced_file_is_caught(self):
        row = list(GOOD_ROW)
        row[6] = "DOES-NOT-EXIST_R1.fastq.gz"
        report = validate_dataset(
            make_csv([row]),
            self.schema,  # file-existence check enabled
            vocabularies=self.vocab,
            metadata=self.metadata,
            source_name="test.csv",
            synthetic=True,
        )
        self.assertIn("file_reference", self.categories(report))

    def test_provenance_block_matches_input(self):
        raw = make_csv([GOOD_ROW, GOOD_ROW_2])
        report = self.validate(raw)
        prov = report["data_provenance"]
        self.assertEqual(prov["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(prov["bytes"], len(raw))
        self.assertEqual(prov["rows_checked"], 2)
        self.assertTrue(prov["synthetic"])
        self.assertEqual(report["tool_version"], "0.1.0")
        self.assertIn("generated_at_utc", report)
        self.assertEqual(report["schema"]["name"], "genomics_sample_sheet")

    def test_bad_demo_sheet_flags_every_seeded_defect_category(self):
        raw = (DATA / "synthetic_sample_sheet_bad.csv").read_bytes()
        report = validate_dataset(
            raw, self.schema, vocabularies=self.vocab,
            metadata=self.metadata, source_name="synthetic_sample_sheet_bad.csv",
            synthetic=True,
        )
        cats = set(self.categories(report))
        for expected in ("required_field", "controlled_vocabulary",
                         "duplicates", "range", "schema", "file_reference"):
            self.assertIn(expected, cats, f"missing category {expected}")
        self.assertEqual(report["data_provenance"]["rows_checked"], 40)


if __name__ == "__main__":
    unittest.main()
