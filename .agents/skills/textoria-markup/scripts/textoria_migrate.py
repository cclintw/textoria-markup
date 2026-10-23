#!/usr/bin/env python3
"""Copy legacy collections into textoria-markup without changing saved IDs/text/tags."""
import argparse,copy,hashlib,json,shutil,tarfile
from pathlib import Path
from textoria_corpus import load_corpus,save_corpus,content_text
from textoria_rebuild import rebuild


def migrate(project):
    project=Path(project).resolve();old=project/'textoria';new=project/'textoria-markup'
    if not old.is_dir():raise ValueError('No legacy textoria directory.')
    if new.exists():raise ValueError('Destination exists; migration never overwrites a collection.')
    old_roots=[p for p in (old/'collections').iterdir() if (p/'corpus.json').exists()]
    report={};new.mkdir()
    for source in old_roots:
        payload=copy.deepcopy(load_corpus(source));dest=new/'collections'/source.name
        if (source/'intermediate/paragraphs.json').exists():
            if json.loads((source/'intermediate/paragraphs.json').read_text())['paragraphs']!=payload['paragraphs']:raise ValueError('Legacy corpus is stale relative to paragraph edits: '+source.name)
        if (source/'intermediate/divisions.json').exists():
            if json.loads((source/'intermediate/divisions.json').read_text())['divisions']!=payload['divisions']:raise ValueError('Legacy corpus is stale relative to divisions: '+source.name)
        dest.mkdir(parents=True);uploads=dest/'uploads';uploads.mkdir()
        for relative,label in [('raw/original','source'),('uploads','attachments'),('references','references')]:
            folder=source/relative
            if folder.exists():shutil.copytree(folder,uploads/label,ignore=shutil.ignore_patterns('__pycache__'))
        # source preparation and provenance remain in the master; no duplicate text.
        payload.setdefault('annotation_state',{'rules':[],'imports':[],'exclusions':[],'overlaps':[],'overrides':[]})
        payload['migration']={'from':'corpus-json-v2','original_corpus_sha256':hashlib.sha256((source/'corpus.json').read_bytes()).hexdigest()}
        config=source/'config/structure_rules.json'
        if config.exists():payload['structure_settings']=json.loads(config.read_text())
        for row in payload.get('source_files',[]):
            original=Path(row.get('original_path') or row.get('path') or '')
            candidates=list((uploads/'source').rglob(original.name)) if original.name and (uploads/'source').exists() else []
            if candidates:row['archived_source']=str(candidates[0].relative_to(dest))
        save_corpus(dest,payload);result=rebuild(dest,site=True)
        check=load_corpus(dest);original=load_corpus(source)
        for key in ['documents','divisions','paragraphs','annotation_profile','vocabulary']:
            if check.get(key)!=original.get(key):raise ValueError('Migration changed '+key)
        report[source.name]={'counts':result['counts'],'ids_text_and_annotations_preserved':True}
    # Existing epub exports are deliverables and must not disappear during cleanup.
    for source in old_roots:
        for path in (source/'epub').glob('*.epub'):shutil.copy2(path,new/'collections'/source.name/'exports'/path.name)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project',type=Path);a=p.parse_args();print(json.dumps(migrate(a.project),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
