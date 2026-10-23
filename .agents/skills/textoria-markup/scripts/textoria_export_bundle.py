#!/usr/bin/env python3
"""Current public exports: self-contained reader HTML, metadata tables, DocuXML."""
import argparse,csv,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
from textoria_corpus import load_snapshot,corpus_revision
from textoria_common import corpus_lock
from textoria_export_docusky import docuxml_document,validate_docuxml,metadata_rows,records
from textoria_export_reader import standalone_reader,validate_reader,standalone_guide


def export_document(root,formats=('html','docuxml'),*,node=None,node_modules=None,preview=None,showcase=False):
    root=Path(root).resolve();formats=list(dict.fromkeys(formats))
    if not formats or set(formats)-{'html','table','docuxml'}:raise ValueError('Choose html, table or docuxml.')
    if 'table' in formats and (not node or not node_modules):
        raise ValueError('CSV/Excel export needs the verified bundled Node and artifact-tool modules; resolve runtime paths first.')
    data,revision=load_snapshot(root);stem=re.sub(r'[\\/:*?"<>|\x00-\x1f]','_',data['collection']['title']).strip(' .') or root.name
    folder=root/'exports';folder.mkdir(exist_ok=True);files={}
    with tempfile.TemporaryDirectory(prefix='.export-',dir=root) as temporary:
        stage=Path(temporary)
        if 'html' in formats:
            path=stage/(stem+'.html');help_name=stem+'_help.html'
            path.write_text(standalone_reader(data,stage/'reader-build',showcase=showcase,help_href=help_name),encoding='utf-8')
            if showcase:
                guide=stage/help_name;guide.write_text(standalone_guide(stage/'reader-build',path.name),encoding='utf-8');files['help']=guide
            validate_reader(path,data);files['html']=path
        if 'docuxml' in formats:
            path=stage/(stem+'_docu.xml');path.write_bytes(docuxml_document(data));validate_docuxml(path,data);files['docuxml']=path
        if 'table' in formats:
            columns,rows=metadata_rows(data);path=stage/(stem+'_metadata.csv')
            with path.open('w',encoding='utf-8-sig',newline='') as handle:
                writer=csv.DictWriter(handle,fieldnames=columns);writer.writeheader();writer.writerows(rows)
            with path.open(encoding='utf-8-sig',newline='') as handle:
                if list(csv.DictReader(handle))!=rows:raise ValueError('CSV metadata fidelity failure.')
            files['csv']=path;inputs=stage/'rows.json';inputs.write_text(json.dumps({'columns':columns,'rows':rows},ensure_ascii=False),encoding='utf-8')
            helper=stage/'build_xlsx.mjs';shutil.copy2(Path(__file__).with_name('textoria_metadata_xlsx.mjs'),helper)
            (stage/'node_modules').symlink_to(Path(node_modules).resolve(),target_is_directory=True)
            xlsx=stage/(stem+'_metadata.xlsx');args=[str(node),str(helper),str(inputs),str(xlsx)]
            if preview:args.append(str(preview))
            subprocess.run(args,check=True,capture_output=True,text=True)
            if not xlsx.is_file():raise ValueError('Excel exporter did not produce a workbook.')
            files['xlsx']=xlsx
        outputs={};backups=[];published=[]
        with corpus_lock(root):
            if corpus_revision(root)!=revision:raise ValueError('Corpus changed during export; retry.')
            try:
                for key,path in files.items():
                    target=folder/path.name
                    if target.exists():target.rename(stage/(key+'.backup'));backups.append((key,target))
                    os.replace(path,target);published.append(target);outputs[key]=str(target)
            except Exception:
                for target in published:target.unlink()
                for key,target in backups:(stage/(key+'.backup')).rename(target)
                raise
    return {'ok':True,'files':outputs,'counts':data['counts'],'documents':len(records(data)),'revision':revision}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('collection',type=Path)
    parser.add_argument('--format',required=True,choices=['html','table','docuxml','all']);parser.add_argument('--node');parser.add_argument('--node-modules');parser.add_argument('--preview')
    parser.add_argument('--showcase',action='store_true',help='Retain copy-only action icons and export a same-tab help page.')
    args=parser.parse_args();formats=('html','table','docuxml') if args.format=='all' else (args.format,)
    print(json.dumps(export_document(args.collection,formats,node=args.node,node_modules=args.node_modules,preview=args.preview,showcase=args.showcase),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
