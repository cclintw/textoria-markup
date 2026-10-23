"""Name identities and database-ready projections of the canonical corpus."""
import copy
import hashlib
import json

NAME_KINDS = {'canonical', 'alias', 'courtesy_name', 'sobriquet', 'alternative',
              'abbreviation', 'variant', 'contextual_form', 'unspecified'}


def name_id(term_id, alias):
    value = [term_id, alias['text'], alias.get('scope', {}), alias.get('match_policy', 'contextual')]
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return 'name-' + hashlib.sha256(raw.encode()).hexdigest()[:24]


def matching_name(term, text, paragraph):
    from textoria_annotation import scope_matches
    matches = [a for a in term['aliases'] if a['text'] == text and scope_matches(a, paragraph)]
    if not matches:
        raise ValueError('Annotation has no matching name record: ' + term['term_id'])
    def rank(a):
        scope = a.get('scope', {})
        return (next((i for i, key in enumerate(('paragraph_ids', 'division_ids', 'document_ids'))
                      if key in scope), 3), sum(len(v) for v in scope.values()), name_id(term['term_id'], a))
    return min(matches, key=rank)


def synchronize_names(data):
    """Additive migration; preserves source text, entity and occurrence IDs."""
    from textoria_annotation import iter_annotations
    terms = {t['term_id']: t for t in data.get('vocabulary', {}).get('terms', [])}
    for tid, term in terms.items():
        for alias in term['aliases']:
            expected = name_id(tid, alias)
            if 'name_id' in alias and alias['name_id'] != expected:
                raise ValueError('Stale or mismatched name_id')
            alias['name_id'] = expected
            alias.setdefault('name_kind', 'canonical' if alias['text'] == term['canonical_name'] else 'unspecified')
            if alias['name_kind'] not in NAME_KINDS:
                raise ValueError('Unknown name_kind')
            if alias['name_kind'] == 'canonical' and alias['text'] != term['canonical_name']:
                alias['name_kind'] = 'unspecified'
    for p in data.get('paragraphs', []):
        for node in p['content']:
            if not node.get('annotation'):
                continue
            for ann in iter_annotations(node['annotation']):
                if ann.get('term_id'):
                    ann['name_id'] = matching_name(terms[ann['term_id']], node['text'], p)['name_id']
                for alternative in ann.get('term_alternatives', []):
                    alternative['name_id'] = matching_name(terms[alternative['term_id']], node['text'], p)['name_id']
    data['identity_schema_version'] = '1.0'


def validate_names(data):
    from textoria_annotation import iter_annotations, scope_matches
    terms = {t['term_id']: t for t in data['vocabulary']['terms']}
    for tid, term in terms.items():
        for alias in term['aliases']:
            if alias.get('name_id') != name_id(tid, alias) or alias.get('name_kind') not in NAME_KINDS:
                raise ValueError('Invalid name identity')
            if alias['name_kind'] == 'canonical' and alias['text'] != term['canonical_name']:
                raise ValueError('Canonical name record disagrees with entity')
    for p in data['paragraphs']:
        for node in p['content']:
            if not node.get('annotation'):
                continue
            for ann in iter_annotations(node['annotation']):
                refs = ([ann] if ann.get('term_id') else []) + ann.get('term_alternatives', [])
                for ref in refs:
                    term = terms[ref['term_id']]
                    if not any(a['name_id'] == ref.get('name_id') and a['text'] == node['text']
                               and scope_matches(a, p) for a in term['aliases']):
                        raise ValueError('Name reference has stale text, scope or entity')


def relational_export(data):
    """Derived tables; uncertain identities use alternative links, not a guessed ID."""
    value = copy.deepcopy(data)
    synchronize_names(value)
    entities, names, mentions, links = [], {}, [], []
    terms = {t['term_id']: t for t in value['vocabulary']['terms']}
    for tid, term in terms.items():
        entities.append({'entity_id': tid, 'canonical_name': term['canonical_name'],
                         'markup_ids': term.get('markup_ids', [term['markup_id']]),
                         'sources': copy.deepcopy(term.get('sources', []))})
        for alias in term['aliases']:
            row = {**copy.deepcopy(alias), 'entity_id': tid}
            old = names.get(row['name_id'])
            if old and old['name_kind'] != row['name_kind']:
                raise ValueError('Conflicting kinds for one name record')
            if old:
                old['sources'] = list(dict.fromkeys(old.get('sources', []) + row.get('sources', [])))
            else:
                names[row['name_id']] = row
    from textoria_annotation import iter_annotations
    for p in value.get('paragraphs', []):
        start = 0
        for node in p['content']:
            end = start + len(node['text'])
            if node.get('annotation'):
                for ann in iter_annotations(node['annotation']):
                    refs = ([ann] if ann.get('term_id') else []) + ann.get('term_alternatives', [])
                    resolved = len(refs) == 1
                    mentions.append({'mention_id': ann['id'], 'document_id': p['document_id'],
                                     'division_id': p['division_id'], 'paragraph_id': p['paragraph_id'],
                                     'start': start, 'end': end, 'surface': node['text'],
                                     'markup_ids': ann.get('markup_ids', [ann['markup_id']]),
                                     'identity_status': 'resolved' if resolved else ('ambiguous' if refs else 'unlinked'),
                                     'entity_id': refs[0]['term_id'] if resolved else None,
                                     'name_id': refs[0]['name_id'] if resolved else None})
                    for ref in refs:
                        links.append({'mention_id': ann['id'], 'entity_id': ref['term_id'],
                                      'name_id': ref['name_id'], 'relation': 'resolved' if resolved else 'alternative'})
            start = end
    return {'identity_schema_version': '1.0', 'entities': entities, 'names': list(names.values()),
            'mentions': mentions, 'mention_links': links}



def validate_relational_export(payload):
    """Check foreign keys and vocabulary agreement before round-trip import."""
    if payload.get('identity_schema_version') != '1.0':
        raise ValueError('Unsupported exported identity schema')
    expected = relational_export({'vocabulary': {'terms': payload['terms']}, 'paragraphs': []})
    for key in ('entities', 'names'):
        if payload.get(key) != expected[key]:
            raise ValueError('Relational export disagrees with formal vocabulary: ' + key)
    entities = {r['entity_id']: r for r in payload['entities']}
    names = {r['name_id']: r for r in payload['names']}
    mentions = {}
    for row in payload['mentions']:
        if row['mention_id'] in mentions:
            raise ValueError('Duplicate mention ID')
        if type(row['start']) is not int or type(row['end']) is not int or row['start'] < 0 or row['end'] - row['start'] != len(row['surface']):
            raise ValueError('Invalid mention offsets')
        mentions[row['mention_id']] = row
    groups = {mid: [] for mid in mentions}
    seen = set()
    from textoria_annotation import scope_matches
    for row in payload['mention_links']:
        mid, eid, nid = row['mention_id'], row['entity_id'], row['name_id']
        key = (mid, eid)
        if key in seen or mid not in mentions or eid not in entities or nid not in names:
            raise ValueError('Invalid or duplicate mention foreign key')
        seen.add(key)
        name, mention = names[nid], mentions[mid]
        if name['entity_id'] != eid or name['text'] != mention['surface'] or not scope_matches(name, mention):
            raise ValueError('Mention name, entity, surface or scope disagrees')
        groups[mid].append(row)
    for mid, rows in groups.items():
        mention = mentions[mid]
        status = 'resolved' if len(rows) == 1 else ('ambiguous' if rows else 'unlinked')
        if mention['identity_status'] != status:
            raise ValueError('Inconsistent identity status')
        if status == 'resolved':
            if mention['entity_id'] != rows[0]['entity_id'] or mention['name_id'] != rows[0]['name_id'] or rows[0]['relation'] != 'resolved':
                raise ValueError('Resolved mention foreign key disagrees')
        elif mention['entity_id'] is not None or mention['name_id'] is not None or any(row['relation'] != 'alternative' for row in rows):
            raise ValueError('Unresolved mention must not assert one entity')
    return True
