"""Read external vocabularies, or validated JSON prepared by Codex from prose."""
from __future__ import annotations
import csv,hashlib,json,re,shutil
from pathlib import Path


def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_type(value):
    names={'人物':'person','地點':'place','地名':'place','組織':'organization','機構':'organization','官職':'office','器物':'artifact','關鍵詞':'key-word','keyword':'key-word'}
    return names.get(value.strip(),value.strip())


def read_reference_set(data):
    reference_id = data['id']
    source = 'CBDB' if reference_id == 'cbdb' else data['name']
    entities, ids = [], {}
    for original in data['entities']:
        item = dict(original)
        source_id = item['id']
        term_id = f'{reference_id}-{source_id.replace(":", "-")}'
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*', term_id):
            term_id = 'reference-' + hashlib.sha256(f'{reference_id}:{source_id}'.encode()).hexdigest()[:24]
        item['id'] = term_id
        item.setdefault('source', source)
        item.setdefault('source_id', source_id)
        entities.append(item)
        ids[source_id] = term_id
    relations = [{**row,'subject_id':ids[row['subject_id']],'object_id':ids[row['object_id']]}
                 for row in data['relations']]
    result = {'entities':entities,'relations':relations}
    if isinstance(data.get('rules'),list):result['rules']=data['rules']
    return result


def read_upload(path,kind='auto'):
    path=Path(path)
    if path.suffix.lower()=='.json':
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict):raise ValueError('Normalized upload must be a JSON object.')
        if data.get('schema_version')==1 and {'id','name','entities','relations'}<=data.keys():
            return read_reference_set(data)
        if data.get('schema_version')=='textoria-markup-reference-1':
            from textoria_identity import relational_export
            from textoria_reference_tables import project_tables
            model={'vocabulary':{'terms':data['terms']},'paragraphs':[]}
            expected=project_tables(model)
            if any(data.get(key)!=expected[key] for key in ('entities','names')):
                expected=relational_export(model)
            for key in ('entities','names'):
                if data.pop(key,None)!=expected[key]:
                    raise ValueError('Reference table disagrees with formal vocabulary: '+key)
        if data.get('schema_version')=='textoria-markup-vocabulary-1' and 'identity_schema_version' in data:
            # Relational tables describe the source document. Import the formal
            # vocabulary, not source occurrences or a second set of entities.
            from textoria_identity import validate_relational_export
            validate_relational_export(data)
            for key in ('identity_schema_version','entities','names','mentions','mention_links'):data.pop(key,None)
        return data
    if path.suffix.lower() in {'.csv','.tsv'}:
        with path.open(encoding='utf-8-sig',newline='') as handle:
            reader=csv.DictReader(handle,delimiter='\t' if path.suffix.lower()=='.tsv' else ',');fields=reader.fieldnames or []
            columns={x.strip().lower():x for x in fields}
            name=next((columns[k] for k in ['name','名稱','詞語','正名'] if k in columns),None)
            typ=next((columns[k] for k in ['type','類型','類別'] if k in columns),None)
            alias=next((columns[k] for k in ['alias','別名'] if k in columns),None)
            if kind=='keywords':
                if len(fields)!=1:raise ValueError('Keyword table must have one column.')
                return {'keywords':[row[fields[0]].strip() for row in reader if row.get(fields[0],'').strip()]}
            if not name or not typ:raise ValueError('CSV needs name/type columns; use --keywords for a one-column keyword table, or let Codex normalize unknown columns.')
            entities=[]
            for row in reader:
                if not (row.get(name) or '').strip():continue
                item={'name':row[name].strip(),'types':[normalize_type(x) for x in re.split(r'[|;/；]',row[typ] or '') if x.strip()],
                      'aliases':[x.strip() for x in re.split(r'[|;；]',row.get(alias,'') or '') if x.strip()]}
                for key in ('id','match_policy','source','source_id','url','source_url','latitude','longitude','x_coord','y_coord'):
                    if row.get(columns.get(key)):item[key]=row[columns[key]]
                for key in ('scope','source_refs','location'):
                    if row.get(columns.get(key)):item[key]=json.loads(row[columns[key]])
                kind_value=row.get(columns.get('name_kind'))
                status=row.get(columns.get('name_status'))
                if kind_value or status:
                    forms=[]
                    for value in item['aliases']:
                        form={'text':value,'match_policy':item.get('match_policy','exact'),'scope':item.get('scope',{})}
                        if kind_value:form['name_kind']=kind_value
                        if status:form['evidence']={'identity_status':status}
                        forms.append(form)
                    item['aliases']=forms
                entities.append(item)
            return {'entities':entities}
    if kind=='keywords' and path.suffix.lower() in {'.txt','.md'}:
        return {'keywords':list(dict.fromkeys(x.strip() for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()))}
    raise ValueError('Codex must read and normalize this attachment to JSON (entities/keywords/rules); no automatic entity extraction is performed.')


def prepare_upload(root,source,normalized=None,kind='auto'):
    source=Path(source).resolve();data=read_upload(normalized or source,kind)
    allowed={'entities','keywords','rules','terms','types','exclusions','overrides','relations','schema_version','collection_id'}
    if set(data)-allowed:raise ValueError('Unknown normalized upload fields: '+', '.join(sorted(set(data)-allowed)))
    for key in ['entities','keywords','rules','terms','types','exclusions','overrides','relations']:
        if key in data and not isinstance(data[key],list):raise ValueError(key+' must be a list.')
    folder=Path(root)/'uploads';folder.mkdir(parents=True,exist_ok=True)
    checksum=file_hash(source);target=folder/source.name
    if target.exists() and file_hash(target)!=checksum:target=folder/(source.stem+'-'+checksum[:12]+source.suffix)
    if target.resolve()!=source:shutil.copy2(source,target)
    return data,{'file':str(target.relative_to(root)),'sha256':checksum,'normalized_sha256':hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()}
