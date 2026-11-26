"""Normalize entity references and coordinates for storage and reader output."""

from math import isfinite
import re
from urllib.parse import urlsplit


def optional_text(value):
    if isinstance(value, str):
        return value.strip() or None
    return str(value) if type(value) is int else None


def web_url(value):
    url = optional_text(value)
    if not url or re.search(r'[\s\\]', url):
        return None
    try:
        parsed = urlsplit(url)
        _ = parsed.port
        if parsed.scheme in {'http', 'https'} and parsed.hostname and not parsed.username and not parsed.password:
            return url
    except ValueError:
        pass
    return None


def location_for(row):
    if not isinstance(row, dict):
        return None
    latitude = row.get('latitude', row.get('y_coord'))
    longitude = row.get('longitude', row.get('x_coord'))
    if isinstance(latitude, bool) or isinstance(longitude, bool):
        return None
    try:
        latitude, longitude = float(latitude), float(longitude)
    except (TypeError, ValueError, OverflowError):
        return None
    if not (isfinite(latitude) and isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return {'latitude': latitude, 'longitude': longitude, 'source': optional_text(row.get('source')),
            'source_id': optional_text(row.get('source_id'))}


def source_ref(row, person=False):
    source = optional_text(row.get('source'))
    source_id = optional_text(row.get('source_id'))
    url = web_url(row.get('url') or row.get('source_url'))
    status = 'candidate' if row.get('status') == 'candidate' else 'linked'
    if source and source.casefold() == 'cbdb':
        source = 'CBDB'
        match = re.fullmatch(r'(?:person:)?([0-9]+)', source_id or '')
        if not url and person and status == 'linked' and match:
            url = 'https://cbdb.fas.harvard.edu/cbdbapi/person.php?id=' + match[1]
    if not (source or source_id or url):
        return None
    location = location_for(row.get('location', row))
    if location:
        location['source'] = location['source'] or source
        location['source_id'] = location['source_id'] or source_id
    return {'source': source, 'source_id': source_id, 'url': url, 'status': status, 'location': location}


def merge_refs(rows):
    refs = {}
    for row in rows:
        key = (row['source'], row['source_id'], row['status'], row['url'] if not row['source_id'] else None)
        previous = refs.get(key)
        if previous is None:
            refs[key] = row
        else:
            refs[key] = {**previous, 'url': previous['url'] or row['url'],
                         'location': previous['location'] or row['location']}
    return list(refs.values())


def entity_metadata(row):
    types = row.get('markup_ids') or row.get('types') or [row.get('markup_id') or row.get('type')]
    person = types == ['person']
    rows = list(row.get('source_refs') or [])
    if any(row.get(k) for k in ('source', 'source_id', 'url', 'source_url')):
        direct = {key: row.get(key) for key in ('source', 'source_id', 'url', 'source_url')}
        direct['location'] = location_for(row.get('location', row))
        rows.append(direct)
    for alias in row.get('aliases', []):
        evidence = alias.get('evidence') if isinstance(alias, dict) else None
        if not isinstance(evidence, dict) or not evidence.get('reference_set_id'):
            continue
        candidates = evidence.get('candidate_ids')
        if not isinstance(candidates, list):
            continue
        ref_id = evidence['reference_set_id']
        own_record = len(candidates) == 1 and row.get('term_id') == f'{ref_id}-{candidates[0]}'
        status = 'linked' if len(candidates) == 1 and (own_record or evidence.get('identity_status') == 'linked') else 'candidate'
        rows.extend({'source': evidence['reference_set_id'], 'source_id': candidate, 'status': status}
                    for candidate in candidates)
    refs = merge_refs(ref for original in rows if isinstance(original, dict)
                      if (ref := source_ref(original, person)))
    location = location_for(row.get('location', row))
    if not location:
        linked_locations = [ref['location'] for ref in refs if ref['status'] == 'linked' and ref['location']]
        coordinates = {(point['latitude'], point['longitude']) for point in linked_locations}
        if len(coordinates) == 1:
            location = linked_locations[0]
    if location and not location['source'] and len(refs) == 1 and refs[0]['status'] == 'linked':
        location.update(source=refs[0]['source'], source_id=location['source_id'] or refs[0]['source_id'])
    return {'source_refs': refs, 'location': location}


def merge_entity_metadata(term, incoming, *, keep_location):
    saved = entity_metadata(term)
    term['source_refs'] = merge_refs([*saved['source_refs'], *incoming['source_refs']])
    left, right = saved['location'], incoming['location']
    if left and right and (left['latitude'], left['longitude']) != (right['latitude'], right['longitude']):
        term['location'] = left if keep_location else None
    else:
        term['location'] = left or right


def synchronize_entity_metadata(data):
    for term in data.get('vocabulary', {}).get('terms', []):
        term.update(entity_metadata(term))
