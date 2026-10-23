"""Collection identity and path rules shared by build entry points."""
from __future__ import annotations
import json
import re
from pathlib import Path

SLUG_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"


def validate_slug(slug: str) -> str:
    if not re.fullmatch(SLUG_PATTERN, slug):
        raise ValueError("Collection slug must use lowercase ASCII letters/digits and single hyphens; provide --collection-slug, e.g. bihai-jiyou.")
    return slug


def collection_identity(project_root: Path, output: Path) -> str:
    parent = (project_root / "textoria-markup" / "collections").resolve()
    if output.parent.resolve() != parent or not output.name.startswith("collection-"):
        raise ValueError("Collection output must be textoria-markup/collections/collection-<ASCII-slug>/, including the first collection.")
    validate_slug(output.name[len("collection-"):])
    if output.resolve() != parent / output.name:
        raise ValueError("Collection path must not redirect through a symlink.")
    return output.name


def read_registry(project_root: Path) -> dict:
    path = project_root / "textoria-markup" / "registry.json"
    if not path.exists():
        return {"collections": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("collections"), list):
        raise ValueError("Invalid collection registry; refusing to overwrite it.")
    ids, paths = set(), set()
    for entry in data["collections"]:
        if not isinstance(entry, dict) or not entry.get("collection_id") or not entry.get("path"):
            raise ValueError("Invalid collection registry entry.")
        identity, location = entry["collection_id"], entry["path"]
        if identity in ids or location in paths:
            raise ValueError("Duplicate collection ID or path in registry.")
        if identity.startswith("collection-"):
            validate_slug(identity[len("collection-"):])
            if location != f"textoria-markup/collections/{identity}":
                raise ValueError("Collection registry ID and path do not match.")
        # Old entries remain readable; they are not valid write targets.
        ids.add(identity); paths.add(location)
    return data


def resolve_collection_output(project_root: Path, source: Path, slug: str | None = None, output: Path | None = None) -> Path:
    if output is None:
        slug = validate_slug(slug if slug is not None else source.stem)
        output = project_root / "textoria-markup" / "collections" / f"collection-{slug}"
    identity = collection_identity(project_root, output)
    if slug is not None and identity != f"collection-{validate_slug(slug)}":
        raise ValueError("--collection-slug and --output identify different collections.")
    registry = read_registry(project_root)
    relative = f"textoria-markup/collections/{identity}"
    for entry in registry["collections"]:
        if (entry["collection_id"] == identity or entry["path"] == relative) and (entry["collection_id"], entry["path"]) != (identity, relative):
            raise ValueError("Collection ID or path already belongs to another entry.")
    if output.exists() and any(output.iterdir()):
        path=output/'corpus.json'
        if not path.exists():raise ValueError('Nonempty collection has no corpus.json; refusing to overwrite.')
        data=json.loads(path.read_text())
        if data['collection']['collection_id']!=identity:raise ValueError('Collection identity mismatch.')
    return output
