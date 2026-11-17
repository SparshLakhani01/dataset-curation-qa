# Quality report: synthetic_sample_sheet_bad.csv

- Tool: dataset-curation-qa v0.1.0
- Generated (UTC): 2026-11-16T22:57:11.910167+00:00
- Rows checked: 40
- SHA-256: `069f731c7a8aaa2f12cb71af99f9f247503774ed9714f68164c5a6eb1c122d6b`
- Synthetic data: yes
- Schema: genomics_sample_sheet v1.0.0
- Checks run: 9 (schema_conformance, required_fields, controlled_vocabulary, range, metadata_completeness, missingness, duplicates, outliers, file_references)

## Result

15 issue(s): 13 error(s), 1 warning(s), 1 info flag(s).

## Issues by category

- controlled_vocabulary: 2
- duplicates: 3
- file_reference: 1
- metadata: 2
- outlier: 1
- range: 1
- required_field: 2
- schema: 3

## Column missingness

| column | non-missing | missing | missing rate |
|---|---|---|---|
| sample_id | 40 | 0 | 0.0% |
| donor_id | 39 | 1 | 2.5% |
| tissue | 39 | 1 | 2.5% |
| assay | 40 | 0 | 0.0% |
| donor_age | 40 | 0 | 0.0% |
| donor_sex | 40 | 0 | 0.0% |
| file_path | 40 | 0 | 0.0% |
| collection_date | 40 | 0 | 0.0% |

## Issues (showing 15 of 15)

- [error] controlled_vocabulary (row 9 assay): Value 'Proteomics' is not in the 'assay' controlled vocabulary ['ATAC-seq', 'RNA-seq', 'WES', 'WGS']
- [error] controlled_vocabulary (row 27 donor_sex): Value 'F' is not in the 'sex' controlled vocabulary ['female', 'male', 'unknown']
- [error] duplicates (row 12 sample_id): Duplicate primary key ('SMP-0003',) (first seen in row 3)
- [warning] duplicates (row 40): Row is an exact duplicate of row 2
- [error] duplicates (row 40 sample_id): Duplicate primary key ('SMP-0002',) (first seen in row 2)
- [error] file_reference (row 24 file_path): Referenced file 'SMP-9999_R1.fastq.gz' does not exist under '/home/hatch/workspace/projects/dataset-curation-qa/data/files'
- [error] metadata: Required dataset metadata field 'creator' is missing or empty
- [error] metadata: Required dataset metadata field 'license' is missing or empty
- [info] outlier (row 15 donor_age): Value 250 lies outside the IQR fence [-8, 100] for column 'donor_age' (statistical flag, not a defect)
- [error] range (row 15 donor_age): Value 250 exceeds maximum 110
- [error] required_field (row 5 tissue): Required field 'tissue' is empty
- [error] required_field (row 30 donor_id): Required field 'donor_id' is empty
- [error] schema (row 18 collection_date): Value '15/03/2025' is not a valid date
- [error] schema (row 21 sample_id): Value 'SMP-ABC' does not match pattern '^SMP-[0-9]{4}$'
- [error] schema (row 33 donor_age): Value 'thirty' is not a valid integer
