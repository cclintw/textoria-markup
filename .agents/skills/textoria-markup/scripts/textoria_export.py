"""Derived formal vocabulary exports; never another editable source of truth."""
import csv,json,os,tempfile
from pathlib import Path
from textoria_annotation_statistics import overview


def reader_paragraphs(data):return [{'paragraph_id':p['paragraph_id'],'division_id':p['division_id'],'paragraph_index':p['paragraph_index'],'text':p['text']} for p in data['paragraphs']]


def export_entities(root,data=None):
    if data is None:
        from textoria_corpus import load_corpus
        data=load_corpus(root)
    folder=Path(root)/'exports';folder.mkdir(parents=True,exist_ok=True)
    # Complete round-trip representation: all vocabulary fields, rules and exclusions.
    payload={'schema_version':'textoria-markup-vocabulary-1','collection_id':data['collection']['collection_id'],
             'terms':data['vocabulary']['terms'],'types':data['annotation_profile']['types'],
             'rules':data.get('annotation_state',{}).get('rules',[]),'exclusions':data.get('annotation_state',{}).get('exclusions',[]),
             'overrides':data.get('annotation_state',{}).get('overrides',[])}
    from textoria_identity import relational_export
    payload.update(relational_export(data))
    from textoria_corpus import atomic_json
    atomic_json(folder/'entity.json',payload)
    summary=overview(data);counts={t['term_id']:t['occurrences'] for t in summary['terms']}
    descriptor,name=tempfile.mkstemp(prefix='.entity-',dir=folder)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8-sig',newline='') as handle:
            writer=csv.writer(handle);writer.writerow(['id','name','type','alias','occurrences','match_policy','scope'])
            for term in data['vocabulary']['terms']:
                # One row per original form and type, with scopes and IDs preserved.
                for alias in term['aliases']:
                    for kind in term.get('markup_ids',[term['markup_id']]):writer.writerow([term['term_id'],term['canonical_name'],kind,alias['text'],counts.get(term['term_id'],0),alias.get('match_policy','exact'),json.dumps(alias.get('scope',{}),ensure_ascii=False,separators=(',',':'))])
        os.replace(name,folder/'entity.csv')
    finally:
        if os.path.exists(name):os.unlink(name)
    return {'json':str(folder/'entity.json'),'csv':str(folder/'entity.csv')}
