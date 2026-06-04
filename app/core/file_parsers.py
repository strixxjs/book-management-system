import csv
import io
import json

from fastapi import UploadFile, HTTPException


async def parse_upload(file: UploadFile) -> list[dict]:
    filename = file.filename or ""
    content = await file.read()

    if filename.endswith(".json"):
        return _parse_json(content)
    elif filename.endswith(".csv"):
        return _parse_csv(content)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Use .json or .csv",
        )


def _parse_json(content: bytes) -> list[dict]:
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON must be a list of objects")
    return data


def _parse_csv(content: bytes) -> list[dict]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"CSV must be UTF-8 encoded: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV must contain at least one row")
    return rows