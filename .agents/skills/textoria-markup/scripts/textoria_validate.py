"""Validate canonical corpus and body/annotation fidelity in generated HTML."""
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from textoria_corpus import content_text,load_corpus,validate_payload
from textoria_annotation import iter_annotations
from textoria_reader_sections import reader_sections


class BodyParser(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.current=None;self.text=[];self.paragraphs={};self.ids=set();self.depth=0;self.mapped={};self.active_map=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('p','div') and a.get('data-paragraph-number'):
            self.current=a['id'];self.text=[];self.depth=0;self.mapped[self.current]=[]
        if self.current:self.depth+=1
        if self.current and 'data-source-start' in a:
            self.active_map=[self.depth,int(a['data-source-start']),int(a['data-source-end']),[]]
        if self.current and tag=='span' and a.get('data-id'):self.ids.add(a['data-id'])
    def handle_data(self,text):
        if self.current:self.text.append(text)
        if self.active_map:self.active_map[3].append(text)
    def handle_endtag(self,tag):
        if self.active_map and self.depth==self.active_map[0]:
            _,start,end,text=self.active_map;self.mapped[self.current].append((start,end,''.join(text)));self.active_map=None
        if self.current:
            self.depth-=1
            if self.depth==0:self.paragraphs[self.current]=''.join(self.text);self.current=None


def display_text(text):
    """Only the explicitly supported note/table syntax is non-visible."""
    if re.match(r'^\|.*\|\n\|[ :|\-]+\|(?:\n|$)',text):
        rows=[]
        for index,line in enumerate(text.splitlines()):
            if index==1:continue
            pipes=[m.start() for m in re.finditer(r'(?<!\\)\|',line)]
            rows.extend(line[a+1:b].strip() for a,b in zip(pipes,pipes[1:]))
        text=''.join(rows)
    return re.sub(r'<span class="note">|</span>','',text) if '<span class="note">' in text else text


def validate_site(site,corpus):
    site=Path(site)
    for name in ['index.html','read.html','assets/help.html','assets/css/reference.css','assets/css/reader-adapter.css','assets/js/reader-adapter.js','assets/js/reader-occurrences.js','data/workbench.js']:
        if not (site/name).is_file():raise ValueError('Missing reader output: '+name)
    bydivision={}
    for p in corpus['paragraphs']:bydivision.setdefault(p['division_id'],[]).append(p)
    for d in corpus['divisions']:
        parser=BodyParser();parser.feed((site/'read'/(d['division_id']+'.html')).read_text())
        visible_ids={section['division_id'] for section in reader_sections(corpus,d['division_id'])}
        paragraphs=[p for p in corpus['paragraphs'] if p['division_id'] in visible_ids]
        if parser.paragraphs!={p['paragraph_id']:display_text(content_text(p['content'])) for p in paragraphs}:raise ValueError('HTML changed paragraph text or IDs: '+d['division_id'])
        for p in paragraphs:
            original=content_text(p['content']);mapped=parser.mapped[p['paragraph_id']]
            if any(original[start:end]!=text for start,end,text in mapped):raise ValueError('Invalid reader source offset: '+p['paragraph_id'])
            if mapped and ''.join(text for _,_,text in mapped)!=parser.paragraphs[p['paragraph_id']]:raise ValueError('Incomplete reader source mapping: '+p['paragraph_id'])
        expected={a['id'] for p in paragraphs for n in p['content'] if n.get('annotation') for a in iter_annotations(n['annotation'])}
        if parser.ids!=expected:raise ValueError('HTML annotation IDs changed: '+d['division_id'])
    return True


def validate_outputs(paths,corpus_path=None,include_epub=False,*,include_site=True,check_intermediates=False):
    try:
        corpus=load_corpus(paths.root)
        if include_site:validate_site(paths.site,corpus)
        return {'ok':True,'counts':validate_payload(corpus),'errors':[]}
    except (ValueError,OSError,KeyError) as exc:return {'ok':False,'errors':[str(exc)]}
