#!/usr/bin/env python3
"""Shared paths and transient source-processing helpers."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TEXTORIA_VERSION = "0.2.0"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".csv"}


@dataclass
class BuildPaths:
    root: Path
    raw_original: Path
    prepared: Path
    intermediate: Path
    clean: Path
    csv: Path
    json: Path
    sqlite: Path
    search: Path
    epub: Path
    site: Path
    site_data: Path
    logs: Path
    stages: Path
    config: Path


CSV_FIELDS = {
    "collections": ["collection_id", "title", "subtitle", "description", "collection_type", "language", "created_at", "updated_at", "metadata_json"],
    "documents": ["document_id", "collection_id", "title", "document_type", "creator", "date", "publisher", "source", "identifier", "language", "rights", "source_file", "source_format", "source_encoding", "sort_key", "char_start", "char_end", "metadata_json"],
    "divisions": ["division_id", "collection_id", "document_id", "parent_division_id", "level", "division_type", "title", "label", "n", "sort_order", "path", "char_start", "char_end", "metadata_json"],
    "paragraphs": ["paragraph_id", "collection_id", "document_id", "division_id", "paragraph_index", "text", "char_start", "char_end", "source_file", "metadata_json"],
    "sentences": ["sentence_id", "collection_id", "document_id", "division_id", "paragraph_id", "sentence_index", "text", "char_start", "char_end", "metadata_json"],
    "tokens": ["token_id", "collection_id", "document_id", "division_id", "paragraph_id", "sentence_id", "token_index", "text", "normalized_text", "char_start", "char_end", "token_type", "metadata_json"],
    "source_files": ["source_file_id", "collection_id", "document_id", "original_path", "prepared_path", "extracted_text_path", "file_format", "detected_encoding", "byte_size", "line_count", "sha256", "sort_order", "metadata_json"],
    "metadata": ["metadata_id", "subject_table", "subject_id", "key", "value", "scheme", "language", "source"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dirs(output: Path, *, create: bool = True, transient: bool = False) -> BuildPaths:
    paths = BuildPaths(
        root=output,
        raw_original=output / "raw" / "original",
        prepared=output / "prepared",
        intermediate=output / "intermediate",
        clean=output / "clean",
        csv=output / "csv",
        json=output / "json",
        sqlite=output / "sqlite",
        search=output / "search",
        epub=output / "exports",
        site=output / "site",
        site_data=output / "site" / "data",
        logs=output / ".history" / "reports",
        stages=output / ".history" / "reports" / "stages",
        config=output / "config",
    )
    if create:
        for name in (("root", "raw_original", "prepared", "intermediate", "clean", "logs", "stages", "config") if transient else ("root",)):
            getattr(paths, name).mkdir(parents=True, exist_ok=True)
    return paths


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def make_toc(divisions: list[dict]) -> list[dict]:
    return [
        {
            "id": div["division_id"],
            "type": div["division_type"],
            "title": div["title"],
            "parent_id": div["parent_division_id"],
            "level": div["level"],
            "order": div["sort_order"],
            "path": div["path"],
            "href": f"read/{div['division_id']}.html",
        }
        for div in divisions
    ]


def slugify(value: str, fallback: str = "textoria") -> str:
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", value)
    return value.strip("-") or fallback


def write_stage_report(paths: BuildPaths, stage: str, report: dict) -> None:
    report = {"stage": stage, "generated_at": now_iso(), **report}
    return report


from contextlib import contextmanager
@contextmanager
def corpus_lock(root):
    import tempfile,hashlib,os
    lock=Path(tempfile.gettempdir())/('textoria-markup-'+hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()+'.lock')
    with lock.open('a+b') as handle:
        if os.name=='nt':
            import msvcrt
            handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX)
        try:yield
        finally:
            if os.name=='nt':handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle,fcntl.LOCK_UN)
