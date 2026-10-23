"""DocuXML and matching metadata rows, one top-level division per record."""
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import defaultdict
from textoria_annotation import iter_annotations
from textoria_corpus import content_text

BUILTINS={'person':'PersonName','place':'LocName','office':'Office','official_title':'Office','date':'Date'}

def tag_for(mid):
    return BUILTINS.get(mid,'Udef_'+''.join(part.capitalize() for part in mid.replace('-','_').split('_')))

def records(data):
    divs={d['division_id']:d for d in data['divisions']};byroot=defaultdict(list)
    for p in data['paragraphs']:
        d=divs[p['division_id']];seen=set()
        while d.get('parent_division_id'):
            if d['division_id'] in seen:raise ValueError('Cyclic chapter structure.')
            seen.add(d['division_id']);d=divs[d['parent_division_id']]
        byroot[d['division_id']].append(p)
    docs={d['document_id']:d for d in data['documents']};rows=[]
    for division in data['divisions']:
        if division.get('parent_division_id'):continue
        document=docs[division['document_id']];paragraphs=byroot[division['division_id']]
        rows.append({'filename':data['collection']['collection_id']+'_'+division['division_id'],
                     'corpus':data['collection']['title'],'compilation_name':document['title'],
                     'title':division['title'],'author':document.get('creator',''),
                     'time_orig_str':document.get('date',''),'doc_source':document.get('source',''),
                     'division':division,'paragraphs':paragraphs})
    return rows

def metadata_rows(data):
    columns=['filename','corpus','compilation_name','title','author','time_orig_str','doc_source',
             'metadata/TextoriaDocumentId','metadata/TextoriaDivisionId','metadata/TextoriaDivisionPath']
    rows=[]
    for record in records(data):
        d=record['division']
        row={**{k:record[k] for k in columns[:7]},'metadata/TextoriaDocumentId':d['document_id'],
             'metadata/TextoriaDivisionId':d['division_id'],'metadata/TextoriaDivisionPath':d['path']}
        rows.append(row)
    return columns,rows

def append_text(parent,text):
    if len(parent):parent[-1].tail=(parent[-1].tail or '')+text
    else:parent.text=(parent.text or '')+text

def inline(parent,node,data):
    if not node.get('annotation'):append_text(parent,node['text']);return
    terms={t['term_id']:t for t in data['vocabulary']['terms']}
    host=parent
    for ann in iter_annotations(node['annotation']):
        refs=[ann['term_id']] if ann.get('term_id') else []
        refs += [a['term_id'] for a in ann.get('term_alternatives',[])]
        pairs=[(terms[tid],mid) for tid in refs for mid in terms[tid].get('markup_ids',[terms[tid]['markup_id']])] if refs else [(None,mid) for mid in ann.get('markup_ids',[ann['markup_id']])]
        for term,mid in pairs:
            attrs={'Term':term['canonical_name'] if term else node['text']}
            # Local IDs are provenance, not external authority RefId values.
            host=ET.SubElement(host,tag_for(mid),attrs)
    host.text=node['text']

def docuxml_document(data):
    root=ET.Element('ThdlPrototypeExport');corpus=ET.SubElement(root,'corpus',name=data['collection']['title'])
    settings=ET.SubElement(corpus,'metadata_field_settings')
    ET.SubElement(settings,'compilation_name',show_spotlight='Y',display_order='1').text='文本'
    feature=ET.SubElement(corpus,'feature_analysis');types={t['markup_id']:t for t in data['annotation_profile']['types']}
    used=list(dict.fromkeys(mid for p in data['paragraphs'] for n in p['content'] if n.get('annotation') for a in iter_annotations(n['annotation']) for mid in a.get('markup_ids',[a['markup_id']])))
    tag_sources=defaultdict(list)
    for mid in used:tag_sources[tag_for(mid)].append(mid)
    custom_tags=[(tag,mids) for tag,mids in tag_sources.items() if tag.startswith('Udef_')]
    for index,(tag,mids) in enumerate(custom_tags,1):
        category=tag
        labels=list(dict.fromkeys(types[mid]['label'] for mid in mids))
        ET.SubElement(feature,'spotlight',category=category,sub_category='-',display_order=str(index),title='／'.join(labels))
        ET.SubElement(feature,'tag',type='contentTagging',name=tag,default_category=category,default_sub_category='-')
    documents=ET.SubElement(root,'documents');divisions={d['division_id']:d for d in data['divisions']}
    for record in records(data):
        d=ET.SubElement(documents,'document',filename=record['filename'])
        for field in ['corpus','compilation_name','title','author','time_orig_str','doc_source']:
            if record[field]:ET.SubElement(d,field).text=record[field]
        subtree=[]
        for candidate in data['divisions']:
            current=candidate;seen=set()
            while current['division_id']!=record['division']['division_id'] and current.get('parent_division_id'):
                if current['division_id'] in seen:raise ValueError('Cyclic chapter structure.')
                seen.add(current['division_id']);current=divisions[current['parent_division_id']]
            if current['division_id']==record['division']['division_id']:subtree.append(candidate)
        meta=ET.SubElement(d,'xml_metadata')
        ET.SubElement(meta,'TextoriaDocumentId').text=record['division']['document_id']
        ET.SubElement(meta,'TextoriaDivisionId').text=record['division']['division_id']
        ET.SubElement(meta,'TextoriaDivisionPath').text=record['division']['path']
        ET.SubElement(meta,'TextoriaStructure').text=json.dumps([{'id':v['division_id'],'parent':v.get('parent_division_id',''),'level':v['level'],'title':v['title'],'order':v.get('sort_order',0)} for v in subtree],ensure_ascii=False)
        provenance=[];content=ET.SubElement(d,'doc_content')
        for p in record['paragraphs']:
            dv=divisions[p['division_id']];para=ET.SubElement(content,'Paragraph',Key=p['paragraph_id'],Type=dv['division_id'],Title=dv['path'])
            offset=0
            for node in p['content']:
                inline(para,node,data)
                if node.get('annotation'):provenance.append({'paragraph_id':p['paragraph_id'],'start':offset,'end':offset+len(node['text']),'annotation':node['annotation']})
                offset+=len(node['text'])
        ET.SubElement(meta,'TextoriaAnnotations').text=json.dumps(provenance,ensure_ascii=False,separators=(',',':'))
    # Mixed content must not be pretty-printed; whitespace is original text.
    serialized=ET.tostring(root,encoding='unicode')
    # DocuSky's validator recognizes ASCII tags and requires &quot; even in
    # element text (including JSON). Escape only text, never tag delimiters.
    pieces=re.split(r'(<[^>]*>)',serialized)
    serialized=''.join(piece if i%2 else piece.replace('"','&quot;') for i,piece in enumerate(pieces))
    return ('<?xml version="1.0" encoding="utf-8"?>\n'+serialized).encode('utf-8')

def validate_validator_syntax(text):
    """Check the official DocuxmlValidator's lexical restrictions locally.

    These are stricter than XML: Chinese names, empty attributes and literal
    double quotes in text are rejected. This is not a live database import.
    """
    label=re.compile(r'<\s*/?\s*[a-zA-Z0-9_.]+(\s+[a-zA-Z0-9_]+="[^"]+")*\s*/?\s*>')
    illegal=re.compile(r'<|>|"|&(?!(?:lt|gt|amp|apos|quot);)(?:[^;]+;)?')
    start=text.find('<ThdlPrototypeExport')
    if start<0:raise ValueError('Missing DocuXML root.')
    text=text[start:];cursor=0;stack=[]
    for match in label.finditer(text):
        if illegal.search(text[cursor:match.start()]):
            raise ValueError('DocuSky validator cannot recognize a tag or special symbol.')
        token=match.group();name=re.search(r'[a-zA-Z0-9_.]+',token).group()
        for attribute in re.findall(r'="([^"]+)"',token):
            if illegal.search(attribute):raise ValueError('DocuSky validator rejects an attribute symbol.')
        if re.match(r'<\s*/',token):
            if not stack or stack.pop()!=name:raise ValueError('DocuSky validator nesting mismatch.')
        elif not re.search(r'/\s*>$',token):stack.append(name)
        cursor=match.end()
    if text[cursor:].strip() or stack:raise ValueError('DocuSky validator found incomplete XML.')
    return True


def validate_docuxml(path,data):
    validate_validator_syntax(Path(path).read_text(encoding='utf-8'))
    root=ET.parse(path).getroot()
    if root.tag!='ThdlPrototypeExport':raise ValueError('Wrong DocuXML root.')
    docs=root.findall('./documents/document');names=[d.get('filename') for d in docs]
    if len(names)!=len(set(names)) or len(docs)!=len(records(data)):raise ValueError('Incorrect DocuXML records.')
    feature=root.find('./corpus/feature_analysis')
    declarations={} if feature is None else {t.get('name'):t for t in feature.findall('tag')}
    spotlights=[] if feature is None else feature.findall('spotlight')
    if any(not name or not name.startswith('Udef_') for name in declarations):
        raise ValueError('feature_analysis declarations must use Udef_ custom tags.')
    if [s.get('display_order') for s in spotlights]!=[str(i) for i in range(1,len(spotlights)+1)]:
        raise ValueError('Custom spotlight ordering must start at one and be consecutive.')
    spotlight_pairs={(s.get('category'),s.get('sub_category')) for s in spotlights}
    allowed=set(BUILTINS.values())|{'Paragraph'}
    for element in root.findall('./documents/document/doc_content'):
        for tag in element.iter():
            if tag is element:continue
            if tag.tag in allowed:continue
            if not tag.tag.startswith('Udef_') or tag.tag not in declarations:
                raise ValueError('Unsupported or undeclared DocuXML content tag: '+tag.tag)
            declaration=declarations[tag.tag]
            if declaration.get('type')!='contentTagging' or (declaration.get('default_category'),declaration.get('default_sub_category')) not in spotlight_pairs:
                raise ValueError('Custom tag has no matching contentTagging spotlight.')
    actual={};provenance=[]
    for d in docs:
        if not d.get('filename') or not d.findtext('corpus'):
            raise ValueError('DocuXML requires nonempty filename and corpus.')
        for p in d.findall('./doc_content/Paragraph'):
            if p.get('Key') in actual:raise ValueError('Duplicate exported paragraph.')
            actual[p.get('Key')]=''.join(p.itertext())
        provenance+=json.loads(d.findtext('./xml_metadata/TextoriaAnnotations','[]'))
    if actual!={p['paragraph_id']:content_text(p['content']) for p in data['paragraphs']}:raise ValueError('DocuXML paragraph fidelity failure.')
    actual_ids={a['id'] for row in provenance for a in iter_annotations(row['annotation'])}
    expected={a['id'] for p in data['paragraphs'] for n in p['content'] if n.get('annotation') for a in iter_annotations(n['annotation'])}
    if actual_ids!=expected:raise ValueError('DocuXML annotation provenance mismatch.')
    return True
