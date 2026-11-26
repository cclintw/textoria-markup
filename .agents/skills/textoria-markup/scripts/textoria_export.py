"""Derived formal vocabulary exports; never another editable source of truth."""
from pathlib import Path
from textoria_reference_tables import compile_reference, project_tables


def reader_paragraphs(data):return [{'paragraph_id':p['paragraph_id'],'division_id':p['division_id'],'paragraph_index':p['paragraph_index'],'text':p['text']} for p in data['paragraphs']]


def export_entities(root,data=None,tables=None):
    if data is None:
        from textoria_corpus import load_corpus
        data=load_corpus(root)
    folder=Path(root)/'exports';folder.mkdir(parents=True,exist_ok=True)
    payload=compile_reference(data,project_tables(data) if tables is None else tables)
    from textoria_corpus import atomic_json
    atomic_json(folder/'entity.json',payload)
    return {'json':str(folder/'entity.json')}
