#!/usr/bin/env python3
"""Validate corpus and transactionally regenerate its reader and formal exports."""
import argparse,json,shutil,tempfile
from pathlib import Path
from textoria_corpus import load_corpus,load_snapshot,to_render_data,corpus_revision
from textoria_common import ensure_dirs,corpus_lock
from textoria_export import export_entities
from textoria_reference_tables import FIELDS, REFERENCE_DIR, project_tables, read_working_tables, reference_revision, write_tables


def rebuild(root,*,site=False,site_only=False,exports=None):
    root=Path(root).resolve();corpus,rev=load_snapshot(root)
    # Structure-only corpora have default type definitions, not a vocabulary export.
    state=corpus.get('annotation_state',{})
    if exports is None:
        exports=bool(corpus.get('vocabulary',{}).get('terms') or corpus['counts'].get('annotations')
                     or any(state.get(key) for key in ('imports','rules','exclusions','overrides')))
    ref_revision=reference_revision(root) if exports else None
    publish_tables=exports and (ref_revision is None or ref_revision==state.get('reference_input_revision'))
    exported={'json':str(root/'exports/entity.json'),
              'working_csv':{name:str(root/REFERENCE_DIR/f'{name}.csv') for name in FIELDS}} if exports else {}
    with tempfile.TemporaryDirectory(prefix='.publish-',dir=root) as temporary:
        stage=Path(temporary);paths=ensure_dirs(stage)
        if exports:
            if (root/'exports').exists():shutil.copytree(root/'exports',stage/'exports')
            (stage/'exports/entity.csv').unlink(missing_ok=True)
            tables=None
            if publish_tables:
                write_tables(stage/REFERENCE_DIR,project_tables(corpus))
                tables,_=read_working_tables(stage)
            export_entities(stage,corpus,tables)
        if site or site_only:
            from textoria_build_site import build_static_site
            from textoria_validate import validate_site
            data=to_render_data(corpus);data['_revision']=rev
            build_static_site(paths,data)
            validate_site(stage/'site',corpus)
        names=(['exports'] if exports else [])+([REFERENCE_DIR] if publish_tables else [])+(['site'] if site or site_only else [])
        moved=[];published=[]
        with corpus_lock(root):
            if corpus_revision(root)!=rev:raise ValueError('Corpus changed during publication; rerun rebuild.')
            if publish_tables and reference_revision(root)!=ref_revision:
                raise ValueError('工作詞表在發布期間有變更，請重新讀取後套用。')
            try:
                for name in names:
                    old=root/name
                    old.parent.mkdir(parents=True,exist_ok=True)
                    if old.exists():old.rename(stage/('old-'+Path(name).name));moved.append(name)
                    (stage/name).rename(old);published.append(name)
            except Exception:
                for name in reversed(published):shutil.rmtree(root/name)
                for name in reversed(moved):(stage/('old-'+Path(name).name)).rename(root/name)
                raise
    return {'ok':True,'corpus':str(root/'corpus.json'),'revision':rev,'counts':corpus['counts'],'site_rebuilt':bool(site or site_only),'exports':exported}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('collection',type=Path);p.add_argument('--site',action='store_true');p.add_argument('--site-only',action='store_true');p.add_argument('--export',dest='exports',action='store_true',default=None,help='Explicitly export vocabulary, including an empty one.');a=p.parse_args();print(json.dumps(rebuild(a.collection,site=a.site,site_only=a.site_only,exports=a.exports),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
