"""Optional FastAPI service for dataset-curation-qa.

Endpoints:
  GET  /health    -> {"status": "ok", "tool_version": ...}
  POST /validate  -> accepts a JSON body with the CSV text, schema,
                     vocabularies, and metadata; returns the same JSON
                     quality report the CLI produces.

Requires fastapi + uvicorn (see requirements.txt). Run from the
project root:

    .venv/bin/uvicorn api:app --port 8000

File-existence checks are skipped by the API: uploaded content has no
on-disk base directory, so columns with must_exist are validated for
shape only. The report notes this in the checks_run list.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

from src.validator import TOOL_VERSION, validate_dataset

app = FastAPI(title="dataset-curation-qa")


class ValidateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    filename: str = "upload.csv"
    content: str  # raw CSV text
    schema_: Dict[str, Any] = Field(default={}, alias="schema")
    vocabularies: Dict[str, List[str]] = {}
    metadata: Dict[str, Any] = {}
    synthetic: bool = False
    license: str = ""


@app.get("/health")
def health():
    return {"status": "ok", "tool_version": TOOL_VERSION}


@app.post("/validate")
def validate(payload: ValidateRequest):
    schema = copy.deepcopy(payload.schema_)
    # Uploaded content has no on-disk base directory; skip file checks.
    for col in schema.get("columns", []):
        col.pop("must_exist", None)
    report = validate_dataset(
        payload.content.encode("utf-8"),
        schema,
        vocabularies=payload.vocabularies,
        metadata=payload.metadata,
        source_name=payload.filename,
        synthetic=payload.synthetic,
        license_text=payload.license,
    )
    return report
