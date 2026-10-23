"""Read external vocabularies, or validated JSON prepared by Codex from prose."""
from __future__ import annotations
import csv,hashlib,json,re,shutil
from pathlib import Path


def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize_type(value):
    names={'人物':'person','地點':'place','地名':'place','組織':'organization','機構':'organization','官職':'office','器物':'artifact','關鍵詞':'key-word','keyword':'key-word'}
    return names.get(value.strip(),value.strip())


def read_upload(path,kind='auto'):
    path=Path(path)
    if path.suffix.lower()=='.json':
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict):raise ValueError('Normalized upload must be a JSON object.')
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
                if row.get('id'):item['id']=row['id']
                if row.get('scope'):item['scope']=json.loads(row['scope'])
                if row.get('match_policy'):item['match_policy']=row['match_policy']
                entities.append(item)
            return {'entities':entities}
    if kind=='keywords' and path.suffix.lower() in {'.txt','.md'}:
        return {'keywords':list(dict.fromkeys(x.strip() for x in path.read_text(encoding='utf-8-sig').splitlines() if x.strip()))}
    raise ValueError('Codex must read and normalize this attachment to JSON (entities/keywords/rules); no automatic entity extraction is performed.')


def prepare_upload(root,source,normalized=None,kind='auto'):
    source=Path(source).resolve();data=read_upload(normalized or source,kind)
    allowed={'entities','keywords','rules','terms','types','exclusions','overrides','schema_version','collection_id'}
    if set(data)-allowed:raise ValueError('Unknown normalized upload fields: '+', '.join(sorted(set(data)-allowed)))
    for key in ['entities','keywords','rules','terms','types','exclusions','overrides']:
        if key in data and not isinstance(data[key],list):raise ValueError(key+' must be a list.')
    folder=Path(root)/'uploads';folder.mkdir(parents=True,exist_ok=True)
    checksum=file_hash(source);target=folder/source.name
    if target.exists() and file_hash(target)!=checksum:target=folder/(source.stem+'-'+checksum[:12]+source.suffix)
    if target.resolve()!=source:shutil.copy2(source,target)
    return data,{'file':str(target.relative_to(root)),'sha256':checksum,'normalized_sha256':hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode()).hexdigest()}
