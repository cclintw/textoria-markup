"""Resolve an empty chapter's path to its first readable descendant for display."""
from collections import defaultdict


def reader_sections(data, division_id):
    divisions = {d['division_id']: d for d in data['divisions']}
    paragraphs = defaultdict(list)
    children = defaultdict(list)
    for p in data['paragraphs']:
        paragraphs[p['division_id']].append(p)
    for d in data['divisions']:
        if d.get('parent_division_id'):
            children[d['parent_division_id']].append(d)
    for siblings in children.values():
        siblings.sort(key=lambda d: d.get('sort_order', 0))

    def first_readable_path(did, visited):
        if did in visited:
            raise ValueError('Cycle in reader chapter hierarchy.')
        if paragraphs[did]:
            return [divisions[did]]
        for child in children[did]:
            path = first_readable_path(child['division_id'], visited | {did})
            if path:
                return [divisions[did], *path]
        return []

    # Never borrow content from an unrelated sibling or another document.
    return first_readable_path(division_id, set()) or [divisions[division_id]]
