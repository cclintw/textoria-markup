"""Annotation schemas and vocabulary helpers; corpus.json is the only source."""
from __future__ import annotations
import copy,csv,hashlib,json,math,re
from pathlib import Path
from textoria_collection_paths import collection_identity


VERSION='1.0'

NAME=re.compile(r'^[a-z][a-z0-9_-]*$')

XML_ID=re.compile(r'^[A-Za-z_][A-Za-z0-9_.-]*$')

ELEMENTS={'persName','placeName','orgName','date','time','eventName','title','roleName','rs','term','measure','seg','name','objectName'}

GLOBAL={'type','subtype','ana','cert','resp','source','corresp'}

NAMING={'role','ref','key'}

ELEMENT_ATTRS={e:set(GLOBAL) for e in ELEMENTS}

for e in ('persName','placeName','orgName','eventName','roleName','rs','name','objectName'):ELEMENT_ATTRS[e]|=NAMING
for e in ('term','title'):ELEMENT_ATTRS[e]|={'ref','key'}
for e in ('date','time'):ELEMENT_ATTRS[e]|={'when','from','to','notBefore','notAfter'}
ELEMENT_ATTRS['measure']|={'quantity','unit','unitRef','commodity','atLeast','atMost','min','max'}

FIELDS={'markup_id','label','kind','base_markup','tei_element','tei_attributes','allowed_attributes','definition','enabled','highlight','count_mode'}

SCOPES={'document_ids','division_ids','paragraph_ids'}

STATUSES={'pending','accepted','rejected','applied'}

def write(path,value):
    from textoria_corpus import atomic_json
    atomic_json(path,value)

def read(path):return json.loads(path.read_text(encoding='utf-8'))

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def text_hash(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

def identity(root):return collection_identity(root.parents[2],root)

def check_value(value,spec):
    kind=spec.get('type')
    if kind=='string':valid=isinstance(value,str)
    elif kind=='number':valid=isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
    elif kind=='tokens':valid=isinstance(value,list) and bool(value) and all(isinstance(v,str) and v and not re.search(r'\s',v) for v in value)
    elif kind=='enum':valid=isinstance(value,str) and value in spec.get('values',[])
    else:raise ValueError(f'Unsupported attribute datatype: {kind}')
    if not valid:raise ValueError(f'Invalid {kind} attribute value: {value!r}')
    if kind=='tokens' and 'values' in spec and any(v not in spec['values'] for v in value):raise ValueError('Unknown controlled attribute token.')

def validate_profile(profile):
    if profile.get('schema_version')!=VERSION or not isinstance(profile.get('types'),list):raise ValueError('Invalid annotation profile.')
    types={}
    for row in profile['types']:
        mid=row.get('markup_id','')
        if not NAME.fullmatch(mid) or mid in types:raise ValueError('Duplicate or invalid markup_id.')
        if not row.get('label') or row.get('kind') not in ('element','attribute'):raise ValueError('Markup needs a label and kind.')
        if row['kind']=='element' and row.get('tei_element') not in ELEMENTS:raise ValueError('Unsupported TEI element; extend the reviewed mapping explicitly.')
        if row['kind']=='element' and row.get('base_markup'):raise ValueError('Element markup must not declare base_markup.')
        if row['kind']=='attribute' and row.get('tei_element'):raise ValueError('Attribute markup inherits its TEI element.')
        if not isinstance(row.get('tei_attributes'),dict) or not isinstance(row.get('allowed_attributes'),dict):raise ValueError('Attribute declarations must be objects.')
        if row.get('count_mode') not in ('occurrences','paragraphs','documents','none'):raise ValueError('Unsupported count mode.')
        for key in ('enabled','highlight'):
            if not isinstance(row.get(key),bool):raise ValueError('Profile flags must be boolean.')
        types[mid]=row
    for mid,row in types.items():
        base,defaults=resolve_markup(profile,mid)
        for key,spec in row['allowed_attributes'].items():
            if key not in ELEMENT_ATTRS[base['tei_element']] or spec.get('type') not in ('string','number','tokens','enum'):raise ValueError('Attribute is not in the supported TEI mapping.')
        allowed=base['allowed_attributes']
        for key,value in defaults.items():
            if key not in ELEMENT_ATTRS[base['tei_element']]:raise ValueError('Static attribute is not supported for this TEI element.')
            if key in allowed:check_value(value,allowed[key])
            elif not isinstance(value,str):raise ValueError('Undeclared static attributes must be strings.')
    return types

def resolve_markup(profile,mid,require_enabled=False):
    types={r['markup_id']:r for r in profile.get('types',[])}
    defaults={};seen=set();current=mid
    while True:
        if current in seen or current not in types:raise ValueError('Missing or cyclic markup inheritance.')
        seen.add(current);row=types[current]
        if require_enabled and not row['enabled']:raise ValueError(f'Markup is disabled: {current}')
        for key,value in row['tei_attributes'].items():
            if key=='role' and key in defaults:defaults[key]=list(dict.fromkeys([*value,*defaults[key]]))
            elif key not in defaults:defaults[key]=copy.deepcopy(value)
            elif defaults[key]!=value:raise ValueError('Conflicting inherited TEI attributes.')
        if row['kind']=='element':return row,defaults
        current=row.get('base_markup')

def normalize_alias(alias,sources=None):
    alias={'text':alias} if isinstance(alias,str) else copy.deepcopy(alias)
    if not isinstance(alias,dict) or not isinstance(alias.get('text'),str) or not alias['text']:raise ValueError('Alias needs original text.')
    alias.setdefault('match_policy','contextual');alias.setdefault('scope',{});alias.setdefault('sources',sources or [])
    if alias.get('sources')==['user'] and alias['match_policy']=='contextual':alias.setdefault('name_kind','contextual_form')
    if 'name_kind' in alias:
        from textoria_identity import NAME_KINDS
        if alias['name_kind'] not in NAME_KINDS:raise ValueError('Unknown name_kind.')
    if alias['match_policy'] not in ('contextual','exact'):raise ValueError('Unknown alias match policy.')
    if not isinstance(alias['scope'],dict) or set(alias['scope'])-SCOPES:raise ValueError('Unknown alias scope.')
    for values in alias['scope'].values():
        if not isinstance(values,list) or not values or not all(isinstance(v,str) and v for v in values):raise ValueError('Alias scope must contain nonempty ID lists.')
    return alias

def markup_ids(row,profile,require_enabled=False):
    """Keep the preferred mapping plus all unresolved alternative entity types."""
    ids=row.get('markup_ids',[row.get('markup_id')])
    if not isinstance(ids,list) or not ids or len(set(ids))!=len(ids) or ids[0]!=row.get('markup_id'):
        raise ValueError('markup_ids must be unique, with markup_id first.')
    bases=[resolve_markup(profile,mid,require_enabled)[0]['markup_id'] for mid in ids]
    if any(x in {'keyword','key-word'} for x in bases) and len(ids)>1:
        raise ValueError('Keyword membership is separate from an entity type conflict.')
    expected=len(set(bases))>1 or bool(row.get('identity_conflict'))
    if row.get('conflict',False)!=expected:
        raise ValueError('Alternative entity types require conflict=true; remove it when resolved.')
    return ids

def iter_annotations(annotation):
    yield annotation
    yield from annotation.get('keyword_annotations',[])

def validate_vocabulary(vocabulary,profile,collection_id):
    if not isinstance(vocabulary,dict):raise ValueError('Annotation vocabulary is required.')
    if vocabulary.get('schema_version')!=VERSION or vocabulary.get('collection_id')!=collection_id or not isinstance(vocabulary.get('terms'),list):raise ValueError('Invalid vocabulary or collection identity.')
    terms={}
    for term in vocabulary['terms']:
        tid=term.get('term_id','')
        if not XML_ID.fullmatch(tid) or tid in terms:raise ValueError('Duplicate or invalid term_id.')
        markup_ids(term,profile)
        base,_=resolve_markup(profile,term.get('markup_id'))
        if any(resolve_markup(profile,mid)[0]['markup_id']!=mid for mid in markup_ids(term,profile)):raise ValueError('Vocabulary identity uses element types, not contextual roles.')
        if not isinstance(term.get('canonical_name'),str) or not term['canonical_name']:raise ValueError('Missing canonical name.')
        if not isinstance(term.get('aliases'),list) or not term['aliases']:raise ValueError('A term needs at least one original form.')
        for alias in term['aliases']:normalize_alias(alias)
        terms[tid]=term
    return terms

def scope_matches(alias,paragraph):
    return all(paragraph.get({'document_ids':'document_id','division_ids':'division_id','paragraph_ids':'paragraph_id'}[key]) in values for key,values in alias.get('scope',{}).items())

def annotation_values(annotation,profile,vocabulary,*,text=None,paragraph=None,require_enabled=False):
    if not isinstance(annotation,dict) or not XML_ID.fullmatch(annotation.get('id','')):raise ValueError('Annotation needs an XML-compatible occurrence ID.')
    ids=markup_ids(annotation,profile,require_enabled)
    base,values=resolve_markup(profile,annotation.get('markup_id'),require_enabled)
    attrs=annotation.get('attributes',{})
    if not isinstance(attrs,dict):raise ValueError('Annotation attributes must be an object.')
    for key,value in attrs.items():
        if key not in base['allowed_attributes']:raise ValueError(f'Undeclared attribute: {key}')
        check_value(value,base['allowed_attributes'][key])
        if key in values and key!='role' and values[key]!=value:raise ValueError('Cannot override a fixed markup attribute.')
        values[key]=list(dict.fromkeys([*values.get(key,[]),*value])) if key=='role' else copy.deepcopy(value)
    terms={t['term_id']:t for t in vocabulary.get('terms',[])}
    tid=annotation.get('term_id')
    references=[{'term_id':tid,'markup_id':base['markup_id']}] if tid else []
    alternatives=annotation.get('term_alternatives',[])
    if not isinstance(alternatives,list):raise ValueError('term_alternatives must be a list.')
    if alternatives and (not tid or not annotation.get('conflict')):raise ValueError('Alternative identities require a primary term and conflict flag.')
    references+=alternatives
    seen=set();expected_types=set()
    for ref in references:
        if not isinstance(ref,dict):raise ValueError('Alternative identity must be an object.')
        target=terms.get(ref.get('term_id'))
        if not target or ref['term_id'] in seen or target['markup_id']!=ref.get('markup_id'):
            raise ValueError('Unknown, duplicate or mismatched vocabulary reference.')
        seen.add(ref['term_id'])
        if alternatives and target['markup_id'] in {'keyword','key-word'}:raise ValueError('Keyword membership is not an identity alternative.')
        expected_types.update(resolve_markup(profile,i)[0]['markup_id'] for i in markup_ids(target,profile))
        if text is not None and not any(a['text']==text and (paragraph is None or scope_matches(a,paragraph)) for a in target['aliases']):raise ValueError('Original name or scope is not registered in the vocabulary.')
    if tid:
        if expected_types!={resolve_markup(profile,i)[0]['markup_id'] for i in ids}:raise ValueError('Unknown or mismatched vocabulary reference.')
        reference='ref' if 'ref' in ELEMENT_ATTRS[base['tei_element']] else 'corresp'
        if values.get(reference) not in (None,'#'+tid):raise ValueError('Authority reference conflicts with term_id.')
        values[reference]='#'+tid
    if 'conflict_note' in annotation and (not annotation.get('conflict') or not isinstance(annotation['conflict_note'],str) or not annotation['conflict_note'].strip()):raise ValueError('Conflict note needs a marked conflict and nonempty text.')
    supplements=annotation.get('keyword_annotations',[])
    if not isinstance(supplements,list):raise ValueError('keyword_annotations must be a list.')
    for extra in supplements:
        if extra.get('markup_id') not in {'keyword','key-word'} or 'keyword_annotations' in extra:
            raise ValueError('Only same-span keyword supplements are supported.')
        annotation_values(extra,profile,vocabulary,text=text,paragraph=paragraph,require_enabled=require_enabled)
    return base,values,terms.get(tid)


def default_state(collection_id):
    path=Path(__file__).resolve().parents[1]/'assets/annotation/markup_types.csv'
    rows=[]
    with path.open(encoding='utf-8-sig',newline='') as handle:
        for source in csv.DictReader(handle):
            row={k:v.strip() for k,v in source.items()}
            for key in ('tei_attributes','allowed_attributes'):row[key]=json.loads(row[key] or '{}')
            for key in ('enabled','highlight'):row[key]=row[key]=='true'
            if row['markup_id']=='keyword':row['markup_id']='key-word';row['tei_attributes']={'type':'key-word'}
            rows.append(row)
    profile={'schema_version':VERSION,'collection_id':collection_id,'types':rows,'rules_text':'','profile_revision':''}
    profile['profile_revision']=digest(profile);validate_profile(profile)
    return {'annotation_profile':profile,'vocabulary':{'schema_version':VERSION,'collection_id':collection_id,'terms':[]},
            'annotation_state':{'rules':[],'imports':[],'exclusions':[],'overlaps':[],'overrides':[]}}


def default_type_labels():
    path=Path(__file__).resolve().parents[1]/'assets/annotation/type_labels_zh-TW.json'
    return json.loads(path.read_text(encoding='utf-8'))


def localize_type_labels(data):
    """Replace known slug fallbacks only; keep explicit custom display names."""
    labels=default_type_labels();changed=0
    for spec in data['annotation_profile']['types']:
        mid=spec['markup_id']
        if mid in labels and spec.get('label')==mid:
            spec['label']=labels[mid];changed+=1
    if changed:data['annotation_profile']['profile_revision']=digest(data['annotation_profile']['types'])
    return changed


def ensure_type(data,mid,label=None):
    if not isinstance(mid,str) or not mid.strip():raise ValueError('Type must be nonempty.')
    mid={'keyword':'key-word'}.get(mid,mid)
    known={x['markup_id']:x for x in data['annotation_profile']['types']}
    if mid in known:return mid
    label=label or default_type_labels().get(mid)
    if not NAME.fullmatch(mid):
        label=label or mid;mid='custom_'+digest(mid)[:12]
    if mid not in known:
        base=copy.deepcopy(known['other']);base.update(markup_id=mid,label=label or mid,definition=label or mid,tei_attributes={'type':mid},enabled=True,highlight=True,color=['#e0edf9','#eee4f8','#f8e5da','#e1f0df','#f8edcc'][int(digest(mid)[:4],16)%5])
        data['annotation_profile']['types'].append(base)
        data['annotation_profile']['profile_revision']=digest(data['annotation_profile']['types'])
    return mid


def pack_content(text,spans):
    nodes=[];cursor=0
    for start,end,ann in sorted(spans,key=lambda x:(x[0],x[1])):
        if start<cursor:raise ValueError('Partially overlapping spans require review.')
        if start>cursor:nodes.append({'text':text[cursor:start]})
        nodes.append({'text':text[start:end],'annotation':ann});cursor=end
    if cursor<len(text):nodes.append({'text':text[cursor:]})
    return nodes or [{'text':text}]


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Apply external vocabularies and rules; never extracts entities with AI.')
    parser.add_argument('collection',type=Path);sub=parser.add_subparsers(dest='command',required=True)
    for name in ['apply','rerun']:
        p=sub.add_parser(name)
        if name=='apply':p.add_argument('source',type=Path);p.add_argument('--normalized',type=Path);p.add_argument('--keywords',action='store_true')
        p.add_argument('--confirmed',action='store_true');p.add_argument('--paragraph-id');p.add_argument('--division-id')
    sub.add_parser('statistics')
    args=parser.parse_args()
    if args.command=='statistics':
        from textoria_annotation_statistics import statistics
        result=statistics(args.collection)
    else:
        if not args.confirmed:raise ValueError('Confirm the requested scope in conversation before applying.')
        scope={}
        if args.paragraph_id:scope['paragraph_ids']=[args.paragraph_id]
        if args.division_id:scope['division_ids']=[args.division_id]
        from textoria_annotation_workflow import run
        result=run(args.collection,getattr(args,'source',None),getattr(args,'normalized',None),getattr(args,'keywords',False),scope or None,args.command=='rerun')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
