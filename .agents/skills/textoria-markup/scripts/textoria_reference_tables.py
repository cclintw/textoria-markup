"""Editable CSV reference tables and their lossless JSON compilation."""
from __future__ import annotations

import copy
import csv
from hashlib import sha256
import io
import json
from pathlib import Path

from textoria_annotation import digest, normalize_alias, validate_vocabulary
from textoria_entity_sources import entity_metadata
from textoria_identity import name_id
from textoria_rule_engine import validate_rule


REFERENCE_DIR = Path('intermediate/reference')
FIELDS = {
    'entities': ('entity_id', 'canonical_name', 'markup_ids', 'sources', 'source_refs', 'location', 'metadata_json'),
    'names': ('name_id', 'entity_id', 'text', 'name_kind', 'match_policy', 'scope', 'sources', 'evidence', 'metadata_json'),
    'relations': ('relation_id', 'subject_id', 'type', 'object_id', 'direction', 'scope', 'status', 'evidence', 'metadata_json'),
    'rules': ('id', 'kind', 'type', 'term_id', 'pattern', 'group', 'flags', 'before', 'after',
              'min_length', 'max_length', 'stop_chars', 'exclude', 'scope', 'enabled', 'description', 'metadata_json'),
}
JSON_FIELDS = {'markup_ids', 'sources', 'source_refs', 'location', 'scope', 'evidence', 'enabled',
               'group', 'min_length', 'max_length', 'stop_chars', 'exclude', 'metadata_json'}


def project_tables(data):
    state = data.get('annotation_state', {})
    entities, names = [], {}
    for term in data['vocabulary']['terms']:
        tid = term['term_id']
        entity = {k: v for k, v in term.items() if k not in {'term_id', 'aliases', 'markup_id', 'conflict'}}
        entity.setdefault('markup_ids', [term['markup_id']])
        entities.append({**entity, 'entity_id': tid, **entity_metadata(term)})
        for original in term['aliases']:
            alias = normalize_alias(original)
            uid = name_id(tid, alias)
            alias.setdefault('name_kind', 'canonical' if alias['text'] == term['canonical_name'] else 'unspecified')
            if alias['name_kind'] == 'canonical' and alias['text'] != term['canonical_name']:
                alias['name_kind'] = 'unspecified'
            row = {**alias, 'name_id': uid, 'entity_id': tid}
            previous = names.get(uid)
            if previous:
                row = {**previous, **row, 'sources': list(dict.fromkeys(previous['sources'] + row['sources']))}
            names[uid] = row
    return {'entities': entities, 'names': list(names.values()),
            'relations': copy.deepcopy(state.get('relations', [])), 'rules': copy.deepcopy(state.get('rules', []))}


def write_tables(folder, tables):
    folder.mkdir(parents=True, exist_ok=True)
    for name, fields in FIELDS.items():
        with (folder / f'{name}.csv').open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in tables[name]:
                extra = {key: val for key, val in row.items() if key not in fields}
                values = {key: row[key] for key in fields if key in row}
                if extra:
                    values['metadata_json'] = extra
                writer.writerow({key: json.dumps(val, ensure_ascii=False) if key in JSON_FIELDS else val
                                 for key, val in values.items()})


def working_files(root):
    folder = Path(root) / REFERENCE_DIR
    if not folder.exists():return {}, None
    files = {}
    for name in FIELDS:
        path = folder / f'{name}.csv'
        if not path.is_file():
            raise ValueError(f'工作詞表不完整，缺少 {path.name}。')
        files[name] = path.read_bytes()
    return files, digest({name: sha256(raw).hexdigest() for name, raw in files.items()})


def reference_revision(root):
    return working_files(root)[1]


def read_working_tables(root):
    files, revision = working_files(root)
    if not files:return None, revision
    tables = {}
    for name, raw in files.items():
        fields = FIELDS[name]
        rows = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
        if not rows.fieldnames or len(rows.fieldnames) != len(fields) or set(rows.fieldnames) != set(fields):
            raise ValueError(f'{name}.csv 欄名與工作詞表規格不符。')
        tables[name] = []
        for line, row in enumerate(rows, 2):
            try:
                if None in row or any(val is None for val in row.values()):
                    raise ValueError('欄位數不符。')
                parsed = {key: json.loads(val) if key in JSON_FIELDS else val
                          for key, val in row.items() if val.strip()}
                extra = parsed.pop('metadata_json', {})
                if not isinstance(extra, dict) or set(extra) & set(fields):
                    raise ValueError('metadata_json 必須是物件，且不得重複主要欄位。')
                tables[name].append({**extra, **parsed})
            except ValueError as error:
                raise ValueError(f'{name}.csv 第 {line} 列：{error}') from error
    return tables, revision


def compile_reference(data, tables):
    profile = data['annotation_profile']
    identity = data['collection']['collection_id']
    terms = {}
    for row in tables['entities']:
        tid = row.get('entity_id')
        types = row.get('markup_ids')
        if not isinstance(tid, str) or not tid or tid in terms:
            raise ValueError('實體 ID 必須存在且唯一。')
        if not isinstance(types, list) or not types or any(not isinstance(mid, str) for mid in types):
            raise ValueError(f'實體 {tid} 的 markup_ids 必須是非空字串陣列。')
        term = {k: v for k, v in row.items() if k != 'entity_id'}
        terms[tid] = {**term, 'term_id': tid, 'markup_id': types[0], 'conflict': len(types) > 1, 'aliases': []}
    known_names = set()
    for row in tables['names']:
        tid = row.get('entity_id')
        if tid not in terms:
            raise ValueError(f'名稱表指向不存在的實體 {tid}。')
        form = normalize_alias({k: v for k, v in row.items() if k not in {'entity_id', 'name_id'}})
        uid = name_id(tid, form)
        if uid in known_names:
            raise ValueError(f'名稱表重複：{tid}／{form["text"]}。')
        known_names.add(uid)
        terms[tid]['aliases'].append(form)
    vocabulary = {**data['vocabulary'], 'terms': list(terms.values())}
    validate_vocabulary(vocabulary, profile, identity)
    relations, relation_ids = [], set()
    for row in tables['relations']:
        for key in ('subject_id', 'object_id'):
            if row.get(key) not in terms:
                raise ValueError(f'關係表的 {key} 指向不存在的實體 {row.get(key)}。')
        if not row.get('type'):
            raise ValueError('關係表缺少類型。')
        rid = row.get('relation_id')
        if rid and rid in relation_ids:
            raise ValueError(f'關係 ID 重複：{rid}。')
        if rid:
            relation_ids.add(rid)
        relations.append(row)
    rules, rule_ids = [], set()
    for rule in tables['rules']:
        validate_rule(rule)
        if rule['id'] in rule_ids:
            raise ValueError(f'規則 ID 重複：{rule["id"]}。')
        rule_ids.add(rule['id'])
        from textoria_annotation import resolve_markup
        resolve_markup(profile, rule['type'])
        if 'term_id' in rule and rule['type'] not in terms.get(rule['term_id'], {}).get('markup_ids', []):
            raise ValueError(f'規則 {rule["id"]} 的目標實體或類型無效。')
        rules.append(rule)
    scopes = {scope: {row[key] for row in data[section]}
              for scope, section, key in [('document_ids','documents','document_id'),
                                          ('division_ids','divisions','division_id'),
                                          ('paragraph_ids','paragraphs','paragraph_id')]}
    for entry in [a for t in terms.values() for a in t['aliases']] + rules:
        for key, values in entry.get('scope', {}).items():
            if not set(values) <= scopes[key]:
                raise ValueError(f'工作詞表的 {key} 含有不存在的範圍 ID。')
    # Recompute derived name IDs after edits to a spelling, scope or match policy.
    compiled_data = {**data, 'vocabulary': vocabulary, 'annotation_state': {'relations': relations, 'rules': rules}}
    compiled = project_tables(compiled_data)
    for term in terms.values():
        for alias in term['aliases']:
            alias['name_id'] = name_id(term['term_id'], alias)
        term.update(entity_metadata(term))
    return {'schema_version': 'textoria-markup-reference-1', 'collection_id': identity,
            'types': profile['types'], 'terms': list(terms.values()), **compiled}
