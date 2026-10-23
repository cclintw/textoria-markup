#!/usr/bin/env python3
"""Commit structure from a reviewed Markdown working copy or a confirmed source build."""
import argparse,hashlib,json,shutil,tempfile
from pathlib import Path
from textoria_common import ensure_dirs,SUPPORTED_EXTENSIONS
from textoria_collection_paths import resolve_collection_output
from textoria_intake import plan as intake_plan
from textoria_utf8_converter import prepare_utf8
from textoria_extract_text import extract_plain_text
from textoria_clean_text import clean_text
from textoria_structure import build_structure
from textoria_corpus import from_legacy,save_corpus
from textoria_annotation import default_state
from textoria_rebuild import rebuild


def build(source,project_root,slug,label=None,text_column=None,clean=True,site=True,prepared_md=None,prepared_sha256=None):
    source=Path(source).resolve()
    if prepared_md is None:
        intake_plan(source, project_root, mode='new', slug=slug)
        root=resolve_collection_output(Path(project_root).resolve(),source,slug=slug)
    else:
        resolved=intake_plan(source, project_root, mode='existing', slug=slug)
        root=Path(resolved['target'])
        prepared_md=Path(prepared_md).resolve()
        if prepared_md.parent != (root/'clean').resolve() or prepared_md.suffix.lower() != '.md':
            raise ValueError('Prepared Markdown must belong to this collection clean/ directory.')
        if clean:
            raise ValueError('Use --no-clean with a reviewed Markdown working copy.')
        if not prepared_sha256:
            raise ValueError('Supply the SHA-256 of the working copy reviewed in the structure preview.')
        prepared_bytes=prepared_md.read_bytes()
        if hashlib.sha256(prepared_bytes).hexdigest() != prepared_sha256:
            raise ValueError('Working copy changed after the preview; preview and confirm again.')
        reviewed_text=prepared_bytes.decode('utf-8',errors='strict')
        archived=root/'uploads'/source.name
        if not archived.is_file() or archived.read_bytes()!=source.read_bytes():
            raise ValueError('Source does not match the archived original.')
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:raise ValueError('Supported sources: TXT, Markdown, HTML, CSV.')
    if (root/'corpus.json').exists():raise ValueError('Collection already exists; use annotation/rebuild, not source reprocessing.')
    with tempfile.TemporaryDirectory(prefix='textoria-markup-source-') as temporary:
        paths=ensure_dirs(Path(temporary),transient=True)
        utf=prepare_utf8(source,paths)
        if prepared_md is not None:
            prepared=reviewed_text
        else:
            extracted=extract_plain_text(source,utf['text'],text_column,paths)
            prepared=clean_text(extracted['text'],extracted['plain_path'],paths,utf['manifest']['detected_encoding'])['text'] if clean else extracted['text']
        data=build_structure(prepared,str(source),source.stem);identity=root.name
        data['collections'][0]['title']=label or source.stem
        for value in data.values():
            if isinstance(value,list):
                for row in value:
                    if isinstance(row,dict) and 'collection_id' in row:row['collection_id']=identity
        payload=from_legacy(data,label or source.stem)
        payload.update(default_state(identity))
        payload['source_preparation']={'encoding':utf['manifest']['detected_encoding'],'cleaning_applied':clean,'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    if prepared_md is not None:
        payload['source_preparation'].update({'prepared_path':str(prepared_md.relative_to(root)), 'prepared_sha256':prepared_sha256, 'structure_confirmed':True})
        if hashlib.sha256(prepared_md.read_bytes()).hexdigest()!=prepared_sha256:
            raise ValueError('Working copy changed during structure preparation; preview again.')
    (root/'uploads').mkdir(parents=True,exist_ok=True);destination=root/'uploads'/source.name
    if destination.exists() and destination.read_bytes()!=source.read_bytes():raise ValueError('Different source already exists under the same name.')
    if destination.resolve()!=source:shutil.copy2(source,destination)
    payload['source_files']=[{'document_id':payload['documents'][0]['document_id'],'collection_id':identity,'original_path':str(destination.relative_to(root)),'sha256':payload['source_preparation']['original_sha256']}]
    for p in payload['paragraphs']:p['source_file']=str(destination.relative_to(root))
    save_corpus(root,payload)
    return rebuild(root,site=site)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--project-root',type=Path,default=Path.cwd());p.add_argument('--collection-slug',required=True);p.add_argument('--label');p.add_argument('--text-column');p.add_argument('--no-clean',action='store_true');p.add_argument('--no-site',action='store_true');p.add_argument('--prepared-md',type=Path);p.add_argument('--prepared-sha256');a=p.parse_args()
    print(json.dumps(build(a.source,a.project_root,a.collection_slug,a.label,a.text_column,not a.no_clean,not a.no_site,a.prepared_md,a.prepared_sha256),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
