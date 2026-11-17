# Quality report: iris.csv

- Tool: dataset-curation-qa v0.1.0
- Generated (UTC): 2026-11-16T22:57:11.978016+00:00
- Rows checked: 150
- SHA-256: `6f608b71a7317216319b4d27b4d9bc84e6abd734eda7872b71a458569e2656c0`
- Synthetic data: no
- License: CC BY 4.0 (UCI Machine Learning Repository)
- Schema: iris_measurements v1.0.0
- Checks run: 9 (schema_conformance, required_fields, controlled_vocabulary, range, metadata_completeness, missingness, duplicates, outliers, file_references)

## Result

7 issue(s): 0 error(s), 3 warning(s), 4 info flag(s).

## Issues by category

- duplicates: 3
- outlier: 4

## Column missingness

| column | non-missing | missing | missing rate |
|---|---|---|---|
| sepal_length | 150 | 0 | 0.0% |
| sepal_width | 150 | 0 | 0.0% |
| petal_length | 150 | 0 | 0.0% |
| petal_width | 150 | 0 | 0.0% |
| species | 150 | 0 | 0.0% |

## Issues (showing 7 of 7)

- [warning] duplicates (row 35): Row is an exact duplicate of row 10
- [warning] duplicates (row 38): Row is an exact duplicate of row 10
- [warning] duplicates (row 143): Row is an exact duplicate of row 102
- [info] outlier (row 16 sepal_width): Value 4.4 lies outside the IQR fence [2.05, 4.05] for column 'sepal_width' (statistical flag, not a defect)
- [info] outlier (row 33 sepal_width): Value 4.1 lies outside the IQR fence [2.05, 4.05] for column 'sepal_width' (statistical flag, not a defect)
- [info] outlier (row 34 sepal_width): Value 4.2 lies outside the IQR fence [2.05, 4.05] for column 'sepal_width' (statistical flag, not a defect)
- [info] outlier (row 61 sepal_width): Value 2.0 lies outside the IQR fence [2.05, 4.05] for column 'sepal_width' (statistical flag, not a defect)
