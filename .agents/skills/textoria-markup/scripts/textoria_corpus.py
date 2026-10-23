"""Single authoritative corpus with atomic, revision-checked persistence."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

from textoria_common import now_iso, write_stage_report

SCHEMA_VERSION = '2.0'
INTERMEDIATE_NAMES = ('metadata.json', 'divisions.json', 'paragraphs.json')
ANNOTATION_TYPES = {'person','place','organization','date','time','event','title','office','official_title','plant','food','artifact','measure','term','other','keyword'}


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.'+path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def content_text(content: list) -> str:
    if not isinstance(content, list) or not content:
        raise ValueError('Paragraph content must be a nonempty list.')
    result=[]
    for node in content:
        if not isinstance(node,dict) or not isinstance(node.get('text'),str):
            raise ValueError('Every content node needs an original text string.')
        if set(node)-{'text','annotation'}:
            raise ValueError('Unsupported content node fields; preserve them before extending the schema.')
        annotation=node.get('annotation')
        if annotation is not None:
            if not isinstance(annotation,dict) or not annotation.get('id'):
                raise ValueError('Annotation needs a stable occurrence ID.')
            if 'markup_id' not in annotation and annotation.get('type') not in ANNOTATION_TYPES:
                raise ValueError('Annotation needs a declared markup_id or a supported legacy type.')
            if 'markup_id' in annotation and 'type' in annotation:
                raise ValueError('Do not mix legacy type and profile markup_id in one annotation.')
            if not node['text']:
                raise ValueError('An annotation cannot cover empty text.')
        result.append(node['text'])
    return ''.join(result)


def validate_payload(payload: dict) -> dict:
    if payload.get('schema_version')!=SCHEMA_VERSION:
        raise ValueError('Unsupported corpus schema_version.')
    collection=payload.get('collection',{})
    identity=collection.get('collection_id')
    if not isinstance(identity,str) or not identity.startswith('collection-'):
        raise ValueError('Missing canonical collection ID.')
    if not collection.get('label'):
        raise ValueError('Collection display label is required.')
    def keyed(name,key):
        rows=payload.get(name)
        if not isinstance(rows,list): raise ValueError(f'{name} must be a list.')
        result={}
        for row in rows:
            if not isinstance(row,dict) or not row.get(key) or row[key] in result:
                raise ValueError(f'Missing or duplicate {key}.')
            if row.get('collection_id',identity)!=identity:
                raise ValueError(f'{name} belongs to another collection.')
            result[row[key]]=row
        return result
    docs=keyed('documents','document_id'); divs=keyed('divisions','division_id'); paras=keyed('paragraphs','paragraph_id')
    if not docs:raise ValueError('Corpus needs at least one document.')
    siblings=set()
    for row in divs.values():
        if row.get('document_id') not in docs:raise ValueError('Orphan division document.')
        parent=row.get('parent_division_id') or ''
        if parent:
            if parent not in divs or divs[parent]['document_id']!=row['document_id']:raise ValueError('Orphan or cross-document division parent.')
            if int(row['level'])!=int(divs[parent]['level'])+1:raise ValueError('Invalid division level.')
        elif int(row['level'])!=1:raise ValueError('Top-level division must have level 1.')
        chain=set();current=row
        while current:
            key=current['division_id']
            if key in chain:raise ValueError('Division parent cycle.')
            chain.add(key);current=divs.get(current.get('parent_division_id'))
        sort=int(row['sort_order']);key=(row['document_id'],parent,sort)
        if sort<1 or key in siblings:raise ValueError('Duplicate or invalid division order.')
        siblings.add(key)
    profile=payload.get('annotation_profile');vocabulary=payload.get('vocabulary')
    if profile is not None:
        from textoria_annotation import validate_profile,validate_vocabulary,annotation_values,iter_annotations,resolve_markup
        if profile.get('collection_id')!=identity:raise ValueError('Annotation profile belongs to another collection.')
        validate_profile(profile);validate_vocabulary(vocabulary,profile,identity)
    elif vocabulary is not None:raise ValueError('Vocabulary requires an annotation profile.')
    annotations=set(); paragraph_order=set()
    for row in paras.values():
        if 'text' in row:raise ValueError('Canonical paragraphs use content only, never a duplicate text field.')
        div=divs.get(row.get('division_id'))
        if not div or row.get('document_id')!=div['document_id']:raise ValueError('Orphan or cross-document paragraph.')
        order=int(row['paragraph_index']);key=(row['document_id'],order)
        if order<1 or key in paragraph_order:raise ValueError('Duplicate or invalid paragraph order.')
        paragraph_order.add(key)
        if not content_text(row.get('content')).strip():raise ValueError('Empty paragraph.')
        for node in row['content']:
            if node.get('annotation'):
                if 'markup_id' in node['annotation']:
                    if profile is None:raise ValueError('Profile-based annotations require a compiled profile and vocabulary.')
                    annotation_values(node['annotation'],profile,vocabulary,text=node['text'],paragraph=row)
                items=iter_annotations(node['annotation']) if profile is not None else [node['annotation']]
                for item in items:
                    aid=item['id']
                    if aid in annotations:raise ValueError('Duplicate annotation occurrence ID.')
                    annotations.add(aid)
    for row in payload.get('source_files',[]):
        if row.get('document_id') and row['document_id'] not in docs:raise ValueError('Orphan source document.')
        if row.get('collection_id',identity)!=identity:raise ValueError('Source belongs to another collection.')
    store=payload.get('annotation_state',{})
    if not isinstance(store,dict):raise ValueError('annotation_state must be an object.')
    from textoria_rule_engine import validate_rule
    rule_ids=set()
    for rule in store.get('rules',[]):
        validate_rule(rule)
        if rule['id'] in rule_ids:raise ValueError('Duplicate rule ID.')
        rule_ids.add(rule['id']);resolve_markup(profile,rule['type'])
        for key,known in [('paragraph_ids',paras),('division_ids',divs),('document_ids',docs)]:
            if any(value not in known for value in rule.get('scope',{}).get(key,[])):raise ValueError('Rule scope references an unknown ID.')
    for key in ('exclusions','overrides'):
        if not isinstance(store.get(key,[]),list):raise ValueError(key+' must be a list.')
        for entry in store.get(key,[]):
            if not isinstance(entry,dict):raise ValueError('Invalid saved annotation condition.')
            p=paras.get(entry.get('paragraph_id'));start,end=entry.get('start'),entry.get('end')
            if p is None or type(start)!=int or type(end)!=int or not 0<=start<end<=len(content_text(p['content'])):raise ValueError('Saved annotation condition has stale offsets.')
    if payload.get('identity_schema_version') is not None:
        if payload['identity_schema_version'] != '1.0':raise ValueError('Unsupported identity schema.')
        from textoria_identity import validate_names
        validate_names(payload)
    return {'documents':len(docs),'divisions':len(divs),'paragraphs':len(paras),'annotations':len(annotations)}


def from_legacy(data: dict, label: str | None = None) -> dict:
    """Retain all structure/provenance fields; sentences/tokens become derived data."""
    collection=copy.deepcopy(data['collections'][0]);collection['label']=label or collection.get('label') or collection['title']
    payload={'schema_version':SCHEMA_VERSION,'collection':collection,'documents':copy.deepcopy(data['documents']),
             'source_files':copy.deepcopy(data.get('source_files',[])),'metadata':copy.deepcopy(data.get('metadata',[])),
             'structure_report':copy.deepcopy(data.get('structure_report',{})),
             'divisions':copy.deepcopy(data['divisions']),'paragraphs':[]}
    for original in data['paragraphs']:
        row=copy.deepcopy(original)
        if 'content' in row:
            if 'text' in row and row['text']!=content_text(row['content']):raise ValueError('Conflicting paragraph text and content.')
            row.pop('text',None)
        else:
            if 'text' not in row:raise ValueError('Missing legacy paragraph text.')
            row['content']=[{'text':row.pop('text')}]
        payload['paragraphs'].append(row)
    validate_payload(payload)
    return payload


def to_render_data(payload: dict) -> dict:
    """An in-memory adapter, not another editable copy of the text."""
    validate_payload(payload)
    data={'collection':copy.deepcopy(payload['collection']),'collections':[copy.deepcopy(payload['collection'])],**{key:copy.deepcopy(payload.get(key,[])) for key in ('documents','divisions','paragraphs','source_files','metadata')},'structure_report':copy.deepcopy(payload.get('structure_report',{})),'sentences':[],'tokens':[]}
    for key in ('annotation_profile','vocabulary'):
        if key in payload:data[key]=copy.deepcopy(payload[key])
    # Respect editable ordering fields, not incidental JSON array order.
    data['documents'].sort(key=lambda row: row.get('sort_key', row['document_id']))
    children={}
    for row in data['divisions']:
        children.setdefault((row['document_id'],row.get('parent_division_id') or ''),[]).append(row)
    ordered=[]
    def visit(doc,parent=''):
        for row in sorted(children.get((doc,parent),[]),key=lambda row:int(row['sort_order'])):
            ordered.append(row);visit(doc,row['division_id'])
    for doc in data['documents']:visit(doc['document_id'])
    data['divisions']=ordered
    doc_order={d['document_id']:i for i,d in enumerate(data['documents'])}
    data['paragraphs'].sort(key=lambda row:(doc_order[row['document_id']],int(row['paragraph_index'])))
    # No sentence/token persistence or analysis pipeline.
    for row in data['paragraphs']:row['text']=content_text(row['content'])
    return data


def corpus_revision(root):
    path=Path(root)/'corpus.json'
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def load_snapshot(root):
    root=Path(root);raw=(root/'corpus.json').read_bytes();payload=json.loads(raw)
    counts=validate_payload(payload)
    if payload.get('counts')!=counts:raise ValueError('Corpus counts do not match content.')
    if payload['collection']['collection_id']!=root.name:raise ValueError('Collection ID must match directory name.')
    return payload,hashlib.sha256(raw).hexdigest()


def load_corpus(root):return load_snapshot(root)[0]


def save_corpus(root,payload,expected_revision=None):
    import gzip
    from textoria_common import corpus_lock
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    with corpus_lock(root):
        current=corpus_revision(root)
        if expected_revision!=current:raise ValueError('Corpus changed; reload before writing.')
        from textoria_identity import synchronize_names
        synchronize_names(payload)
        payload['counts']=validate_payload(payload)
        payload['storage_format']='textoria-markup-single-corpus-v1'
        payload['generated_at']=now_iso()
        if current:
            folder=root/'.history';folder.mkdir(exist_ok=True)
            backup=folder/(current+'.json.gz')
            if not backup.exists():
                with gzip.open(backup,'wb') as handle:handle.write((root/'corpus.json').read_bytes())
        atomic_json(root/'corpus.json',payload)
    return corpus_revision(root)
