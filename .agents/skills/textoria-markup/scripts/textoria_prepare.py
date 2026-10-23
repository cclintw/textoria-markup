#!/usr/bin/env python3
"""Archive a source and create an editable UTF-8 Markdown; no corpus or site."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from textoria_intake import plan
from textoria_common import ensure_dirs, SUPPORTED_EXTENSIONS
from textoria_utf8_converter import prepare_utf8
from textoria_extract_text import extract_plain_text
from textoria_clean_text import clean_cc_text


def save_new(path, raw):
    if path.exists():
        if path.read_bytes() == raw:
            return
        raise ValueError(f'Refusing to overwrite an existing file: {path}')
    with path.open('xb') as handle:
        handle.write(raw)


def prepare(source, project_root, slug, *, mode='new', text_column=None, profile='preserve'):
    source = Path(source).resolve()
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError('Unsupported source format; use an appropriate format reader first.')
    if profile not in ('preserve', 'cc'):
        raise ValueError('Unknown cleaning profile.')
    resolved = plan(source, project_root, mode=mode, slug=slug)
    root = Path(resolved['target'])
    if (root/'corpus.json').exists():
        raise ValueError('Source preparation for an already structured collection is not supported.')
    # Archive the original immediately after collection selection; never move it.
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != resolved['encoding']['sha256']:
        raise ValueError('Source changed during encoding inspection; inspect again.')
    uploads = root/'uploads'
    uploads.mkdir(parents=True, exist_ok=True)
    saved_source = uploads/source.name
    if saved_source.resolve() != source:
        save_new(saved_source, original)
    with tempfile.TemporaryDirectory(prefix='textoria-prepare-') as temporary:
        paths = ensure_dirs(Path(temporary), transient=True)
        utf = prepare_utf8(saved_source, paths)
        extracted = extract_plain_text(saved_source, utf['text'], text_column, paths)['text']
        if profile == 'cc':
            text, details = clean_cc_text(extracted)
        else:
            text = extracted
            details = {'profile': 'preserve', 'normalization': 'none',
                       'rules_applied': [], 'note': 'Encoding/format preparation only; body and Markdown syntax preserved.'}
    clean_dir = root/'clean'
    clean_dir.mkdir(exist_ok=True)
    clean_path = clean_dir/f'{source.stem}_clean.md'
    clean_bytes = text.encode('utf-8')
    # Never overwrite a working copy the user may have edited.
    save_new(clean_path, clean_bytes)
    report = {'source': str(saved_source.relative_to(root)), 'clean_file': str(clean_path.relative_to(root)),
              'original_sha256': hashlib.sha256(original).hexdigest(),
              'prepared_sha256': hashlib.sha256(clean_bytes).hexdigest(),
              'detected_encoding': utf['manifest']['detected_encoding'],
              'cleaning': details, 'text_column': text_column,
              'structure_confirmed': False}
    save_new(clean_dir/f'{source.stem}_clean.report.json',
             (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    return {'collection': str(root), 'original': str(saved_source), 'clean_file': str(clean_path),
            'prepared_sha256': report['prepared_sha256'], 'corpus_created': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--project-root', type=Path, default=Path.cwd())
    parser.add_argument('--collection-slug', required=True)
    parser.add_argument('--mode', choices=['new', 'existing'], default='new')
    parser.add_argument('--text-column')
    parser.add_argument('--profile', choices=['preserve', 'cc'], default='preserve')
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.project_root, args.collection_slug, mode=args.mode,
                             text_column=args.text_column, profile=args.profile), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
