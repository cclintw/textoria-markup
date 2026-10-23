#!/usr/bin/env python3
"""Textoria UTF-8 preparation stage."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from charset_normalizer import from_bytes

from textoria_common import BuildPaths, SUPPORTED_EXTENSIONS, write_json, write_stage_report


def detect_encoding(raw: bytes) -> tuple[str, float | None]:
    # UTF-32 BOMs must precede UTF-16 because their prefixes overlap.
    for bom, encoding in ((b"\xff\xfe\x00\x00", "utf-32"), (b"\x00\x00\xfe\xff", "utf-32"),
                          (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if raw.startswith(bom):
            return encoding, 1.0
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", 1.0
    try:
        raw.decode("utf-8")
        return "utf-8", 1.0
    except UnicodeDecodeError:
        pass

    result = from_bytes(raw).best()
    if result and result.encoding:
        return result.encoding, getattr(result, "percent_coherence", None)

    raise ValueError("Unable to identify source encoding; refusing guessed or lossy decoding.")


def decode_to_text(raw: bytes, encoding: str) -> str:
    candidates = [encoding]
    if encoding.lower().replace("-", "") in {"big5", "big5hkscs"}:
        candidates = ["big5hkscs", "big5"]
    for candidate in candidates:
        try:
            return raw.decode(candidate, errors="strict")
        except (LookupError, UnicodeDecodeError):
            continue
    raise ValueError(f"Cannot strictly decode source as {encoding}; no replacement characters were inserted.")



def inspect_source_encoding(source: Path) -> dict:
    """Read-only inspection, usable before a collection has been chosen."""
    raw = Path(source).read_bytes()
    encoding, confidence = detect_encoding(raw)
    decoded = decode_to_text(raw, encoding)
    if "\x00" in decoded:
        raise ValueError("Decoded text contains NUL characters; verify encoding or file format.")
    return {"detected_encoding": encoding, "encoding_confidence": confidence,
            "conversion_to_utf8_needed": encoding not in ("utf-8", "utf-8-sig"),
            "replacement_characters": decoded.count("\ufffd"),
            "sha256": hashlib.sha256(raw).hexdigest(), "byte_size": len(raw)}


def normalize_decoded_text(text: str) -> str:
    # Encoding conversion must not normalize punctuation or compatibility glyphs.
    return text.replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff')


def prepare_utf8(source: Path, paths: BuildPaths) -> dict:
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported input format: {source.suffix}")

    raw = source.read_bytes()
    inspection = inspect_source_encoding(source)
    encoding, confidence = inspection["detected_encoding"], inspection["encoding_confidence"]
    decoded = normalize_decoded_text(decode_to_text(raw, encoding))
    source_hash = hashlib.sha256(raw).hexdigest()

    shutil.copy2(source, paths.raw_original / source.name)
    prepared_path = paths.prepared / f"{source.stem}.utf8{source.suffix.lower()}"
    prepared_path.write_text(decoded, encoding="utf-8")

    manifest = {
        "source_file": str(source),
        "extension": source.suffix.lower(),
        "detected_format": source.suffix.lower().lstrip("."),
        "detected_encoding": encoding,
        "encoding_confidence": confidence,
        "byte_size": len(raw),
        "line_count": decoded.count("\n") + 1,
        "has_bom": raw.startswith(b"\xef\xbb\xbf"),
        "readable": True,
        "sha256": source_hash,
        "prepared_path": str(prepared_path),
        "warnings": [],
    }
    write_json(paths.root / "raw" / "source_manifest.json", manifest)
    write_stage_report(paths, "convert_encoding", {"ok": True, "source_manifest": manifest})
    return {"text": decoded, "prepared_path": prepared_path, "manifest": manifest}
