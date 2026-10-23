#!/usr/bin/env python3
"""Read-only collection intake plan; never creates folders or imports a text."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from textoria_collection_paths import collection_identity, validate_slug
from textoria_utf8_converter import inspect_source_encoding


def inventory(project_root: Path) -> list[dict]:
    parent = Path(project_root).resolve() / 'textoria-markup' / 'collections'
    rows = []
    if not parent.exists():
        return rows
    for root in sorted(parent.glob('collection-*')):
        if not root.is_dir():
            continue
        row = {'collection_id': root.name, 'path': str(root), 'usable': False}
        try:
            collection_identity(Path(project_root).resolve(), root)
            corpus = root / 'corpus.json'
            if corpus.exists():
                data = json.loads(corpus.read_text(encoding='utf-8'))
                if data['collection']['collection_id'] != root.name:
                    raise ValueError('Collection identity mismatch.')
                row.update(title=data['collection'].get('title', root.name),
                           documents=len(data.get('documents', [])), usable=True)
            elif not any(root.iterdir()) or (root / 'uploads').is_dir():
                row.update(title=root.name, documents=0, usable=True, preparation_only=True)
            else:
                row['error'] = 'Nonempty collection without a recognized corpus or uploads.'
        except (ValueError, KeyError, TypeError, OSError) as error:
            row['error'] = str(error)
        rows.append(row)
    return rows


def plan(source, project_root, *, mode=None, slug=None) -> dict:
    source = Path(source).resolve()
    project_root = Path(project_root).resolve()
    if not source.is_file():
        raise ValueError('Source file does not exist.')
    choices = inventory(project_root)
    result = {'source': str(source), 'collections': choices, 'writes_files': False,
              'encoding': inspect_source_encoding(source)}
    if mode is None:
        if slug is not None:
            raise ValueError('A slug alone does not specify new versus existing collection.')
        return dict(result, status='needs_collection_choice')
    if mode not in ('new', 'existing'):
        raise ValueError('Choose new or existing collection.')
    if slug is None:
        raise ValueError('Specify the chosen collection slug.')
    root = project_root / 'textoria-markup' / 'collections' / f'collection-{validate_slug(slug)}'
    collection_identity(project_root, root)
    if mode == 'new' and root.exists():
        raise ValueError('New collection target already exists; choose existing or another slug.')
    if mode == 'existing':
        entry = next((c for c in choices if c['collection_id'] == root.name), None)
        if entry is None or not entry['usable']:
            raise ValueError('Existing collection is missing or invalid.')
    return dict(result, status='target_resolved', mode=mode, target=str(root),
                corpus_append_supported=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--project-root', type=Path, default=Path.cwd())
    parser.add_argument('--mode', choices=['new', 'existing'])
    parser.add_argument('--collection-slug')
    args = parser.parse_args()
    print(json.dumps(plan(args.source, args.project_root, mode=args.mode,
                          slug=args.collection_slug), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
