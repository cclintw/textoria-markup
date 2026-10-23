"""Revision-checked dialogue edits. Static HTML never writes canonical data."""
from __future__ import annotations
import argparse,copy,json,uuid
from pathlib import Path
from textoria_annotation import iter_annotations,pack_content,ensure_type,normalize_alias
from textoria_corpus import load_corpus,load_snapshot,save_corpus,corpus_revision,content_text
from textoria_annotation_statistics import overview

revision=corpus_revision


def occurrences(paragraph):
    cursor=0
    for node in paragraph['content']:
        end=cursor+len(node['text'])
        if node.get('annotation'):
            for ann in iter_annotations(node['annotation']):yield cursor,end,ann
        cursor=end


def targets(data,request):
    scope=request.get('scope')
    if scope not in {'occurrence','paragraph','division','all'}:raise ValueError('Confirm scope: occurrence, paragraph, division or all.')
    pid=request.get('paragraph_id');aid=request.get('annotation_id');tid=request.get('term_id')
    anchor=next((p for p in data['paragraphs'] if p['paragraph_id']==pid),None)
    if scope!='all' and not anchor:raise ValueError('Missing paragraph anchor.')
    selected=request.get('annotation_ids')
    if selected is not None:
        if scope!='all' or not isinstance(selected,list) or not selected or any(not isinstance(x,str) or not x for x in selected) or len(selected)!=len(set(selected)):
            raise ValueError('Batch deletion needs all scope and unique nonempty annotation IDs.')
        if request.get('operation')!='delete':raise ValueError('Batch annotation IDs are supported for deletion only.')
        selected=set(selected)
    rows=[]
    for p in data['paragraphs']:
        if scope in {'occurrence','paragraph'} and p['paragraph_id']!=pid:continue
        if scope=='division' and p['division_id']!=anchor['division_id']:continue
        for start,end,ann in occurrences(p):
            if scope=='occurrence' and ann['id']!=aid:continue
            if selected is not None and ann['id'] not in selected:continue
            refs={ann.get('term_id'),*(a['term_id'] for a in ann.get('term_alternatives',[]))}
            if selected is None and scope!='occurrence' and (not tid or tid not in refs):continue
            rows.append((p,start,end,ann))
    if selected is not None and {ann['id'] for _,_,_,ann in rows}!=selected:
        raise ValueError('Batch includes missing or stale annotation IDs; plan again.')
    return rows


def plan(root,request):
    data=load_corpus(root)
    if request.get('operation')=='modify-term' and 'markup_id' in request:
        if request.get('scope')!='all':raise ValueError('Entity master type changes require all scope.')
        rows=targets(data,request)
        return {'revision':revision(root),'affected':len(rows),'operation':'modify-term','scope':'all'}
    if request.get('operation') in {'save','delete'} and request.get('annotation_id') or request.get('operation')=='delete':
        rows=targets(data,request);return {'revision':revision(root),'affected':len(rows),'examples':[{'paragraph_id':p['paragraph_id'],'annotation_id':ann['id'],'text':content_text(p['content'])[a:b]} for p,a,b,ann in rows[:8]]}
    return {'revision':revision(root),'scope':request.get('scope'),'operation':request.get('operation')}


def edit(root,request,*,rebuild_outputs=True):
    if request.get('confirmed') is not True:raise ValueError('Ask the user to confirm the operation and scope before editing.')
    data,rev=load_snapshot(root)
    if request.get('revision')!=rev:raise ValueError('Corpus changed; reload and confirm the affected targets.')
    allowed={'operation','scope','revision','confirmed','paragraph_id','annotation_id','annotation_ids','term_id','start','end','text','markup_id','new_term_id','canonical_name','attributes','note','label','aliases','rule'}
    if set(request)-allowed:raise ValueError('Unknown edit fields; original text is locked.')
    before={p['paragraph_id']:content_text(p['content']) for p in data['paragraphs']}
    store=data.setdefault('annotation_state',{});store.setdefault('exclusions',[]);store.setdefault('overrides',[]);store.setdefault('rules',[])
    operation=request.get('operation');changed=0
    if operation=='undo':
        import gzip
        snapshots=sorted((Path(root)/'.history').glob('*.json.gz'),key=lambda p:p.stat().st_mtime_ns)
        if not snapshots:raise ValueError('No revision available to undo.')
        with gzip.open(snapshots[-1],'rt',encoding='utf-8') as handle:restored=json.load(handle)
        if restored['collection']['collection_id']!=data['collection']['collection_id']:raise ValueError('Snapshot identity mismatch.')
        data=restored;changed=1
    elif operation=='create-type':
        ensure_type(data,request.get('markup_id') or request.get('label',''),request.get('label'));changed=1
    elif operation=='update-rule':
        from textoria_rule_engine import validate_rule
        rule=copy.deepcopy(request['rule']);rule['type']=ensure_type(data,rule.get('type',''));validate_rule(rule)
        index=next((i for i,r in enumerate(store['rules']) if r['id']==rule['id']),None)
        if index is None:raise ValueError('Unknown rule ID.')
        store['rules'][index]=rule;changed=1
    elif operation=='modify-term':
        term=next((t for t in data['vocabulary']['terms'] if t['term_id']==request.get('term_id')),None)
        if not term:raise ValueError('Unknown entity ID.')
        if 'canonical_name' in request:
            if not isinstance(request['canonical_name'],str) or not request['canonical_name'].strip():raise ValueError('Canonical name must be nonempty.')
            term['canonical_name']=request['canonical_name'].strip()
        if 'aliases' in request:
            # Existing original forms must remain valid links; add/modify metadata
            # via explicit alias objects without silently deleting used forms.
            for a in request['aliases']:
                a=normalize_alias(a)
                if not any(old['text']==a['text'] and old.get('scope',{})==a.get('scope',{}) for old in term['aliases']):term['aliases'].append(a)
        if 'markup_id' in request:
            if request.get('scope')!='all':raise ValueError('Entity master type changes require all scope.')
            mid=ensure_type(data,request['markup_id'])
            # Stable identity/aliases remain the shared authority for future reruns.
            term.update(markup_id=mid,markup_ids=[mid],conflict=False)
            term.pop('conflict_note',None)
            known={t['term_id']:t for t in data['vocabulary']['terms']}
            for p in data['paragraphs']:
                for start,end,ann in occurrences(p):
                    refs=[ann.get('term_id'),*(a['term_id'] for a in ann.get('term_alternatives',[]))]
                    if term['term_id'] not in refs:continue
                    kinds=list(dict.fromkeys(kind for tid in refs for kind in known[tid].get('markup_ids',[known[tid]['markup_id']])))
                    ann['markup_id']=kinds[0];ann['markup_ids']=kinds
                    for alternative in ann.get('term_alternatives',[]):
                        alternative['markup_id']=known[alternative['term_id']]['markup_id']
                    ann['conflict']=len(kinds)>1 or len(refs)>1
                    if len(refs)>1 and len(kinds)==1:ann['identity_conflict']=True
                    else:ann.pop('identity_conflict',None)
                    if ann['conflict']:
                        ann.setdefault('conflict_note','保留其他類型或身分，尚未裁決。')
                    else:ann.pop('conflict_note',None)
                    ann['user_confirmed']=True
                    override={'paragraph_id':p['paragraph_id'],'start':start,'end':end,'annotation_id':ann['id'],'term_id':term['term_id']}
                    if override not in store['overrides']:store['overrides'].append(override)
                    changed+=1
        term['user_confirmed']=True
        if 'markup_id' not in request:changed=1
    elif operation in {'save','delete'}:
        wanted=targets(data,request) if request.get('annotation_id') or operation=='delete' else []
        if operation=='delete' and not wanted:raise ValueError('No matching annotations.')
        new=request.get('annotation_id') is None and operation=='save'
        if new:
            scope=request.get('scope');pid=request.get('paragraph_id');text=request.get('text')
            anchor=next((p for p in data['paragraphs'] if p['paragraph_id']==pid),None)
            if not anchor or not isinstance(text,str) or not text:raise ValueError('New annotation needs selected original text and paragraph ID.')
            if scope not in {'occurrence','paragraph','division','all'}:raise ValueError('Confirm annotation scope.')
            for p in data['paragraphs']:
                if scope in {'occurrence','paragraph'} and p['paragraph_id']!=pid:continue
                if scope=='division' and p['division_id']!=anchor['division_id']:continue
                plain=content_text(p['content'])
                if scope=='occurrence':
                    a,b=request.get('start'),request.get('end')
                    if type(a)!=int or type(b)!=int or not 0<=a<b<=len(plain) or plain[a:b]!=text:raise ValueError('Selection offsets or original text are stale.')
                    wanted.append((p,a,b,None))
                else:
                    start=plain.find(text)
                    while start>=0:wanted.append((p,start,start+len(text),None));start=plain.find(text,start+1)
        if not wanted:raise ValueError('No matching annotations.')
        byp={}
        for p,a,b,target in wanted:byp.setdefault(p['paragraph_id'],[]).append((a,b,target))
        for p in data['paragraphs']:
            if p['paragraph_id'] not in byp:continue
            text=content_text(p['content']);spans=[];cursor=0
            for n in p['content']:
                end=cursor+len(n['text'])
                if n.get('annotation'):spans.append((cursor,end,copy.deepcopy(n['annotation'])))
                cursor=end
            for a,b,target in byp[p['paragraph_id']]:
                # Removing a primary annotation preserves its independent keywords.
                host=next((ann for _,_,ann in spans if target and any(x['id']==target['id'] for x in iter_annotations(ann))),None)
                if operation=='delete':
                    for tid in {target.get('term_id'),*(x['term_id'] for x in target.get('term_alternatives',[]))}:
                        store['exclusions'].append({'paragraph_id':p['paragraph_id'],'start':a,'end':b,'term_id':tid})
                    if host['id']==target['id']:
                        spans=[(x,y,ann) for x,y,ann in spans if ann['id']!=target['id']]
                        extras=host.get('keyword_annotations',[])
                        if extras:
                            replacement=copy.deepcopy(extras[0])
                            if len(extras)>1:replacement['keyword_annotations']=copy.deepcopy(extras[1:])
                            spans.append((a,b,replacement))
                    else:host['keyword_annotations']=[x for x in host.get('keyword_annotations',[]) if x['id']!=target['id']]
                else:
                    mid=ensure_type(data,request.get('markup_id') or (target or {}).get('markup_id') or '')
                    if not mid:raise ValueError('Specify annotation type.')
                    name=request.get('canonical_name') or text[a:b];tid=request.get('new_term_id')
                    term=next((t for t in data['vocabulary']['terms'] if t['term_id']==tid),None) if tid else None
                    if not term:
                        term=next((t for t in data['vocabulary']['terms'] if t['canonical_name']==name and t.get('markup_ids',[t['markup_id']])==[mid]),None)
                    if not term:
                        term={'term_id':'manual-'+uuid.uuid4().hex,'canonical_name':name,'markup_id':mid,'markup_ids':[mid],'conflict':False,'aliases':[],'sources':['user'],'user_confirmed':True};data['vocabulary']['terms'].append(term)
                    if not any(x['text']==text[a:b] and x.get('scope',{}).get('paragraph_ids')==[p['paragraph_id']] for x in term['aliases']):term['aliases'].append(normalize_alias({'text':text[a:b],'scope':{'paragraph_ids':[p['paragraph_id']]},'match_policy':'contextual','sources':['user']}))
                    ann={'id':target['id'] if target else 'm-manual-'+uuid.uuid4().hex,'markup_id':mid,'markup_ids':[mid],'term_id':term['term_id'],'attributes':copy.deepcopy(request.get('attributes',(target or {}).get('attributes',{}))),'conflict':False,'user_confirmed':True}
                    if 'note' in request:ann['editor_note']=request['note']
                    if target and host['id']==target['id']:
                        if host.get('keyword_annotations'):ann['keyword_annotations']=host['keyword_annotations']
                        spans=[(x,y,old) for x,y,old in spans if old['id']!=target['id']]
                    elif target:
                        if mid not in {'keyword','key-word'}:raise ValueError('Same-span keyword edits must retain keyword type.')
                        host['keyword_annotations']=[ann if x['id']==target['id'] else x for x in host['keyword_annotations']];changed+=1;continue
                    overlapping=[span for span in spans if a<span[1] and b>span[0]]
                    if overlapping:
                        if mid in {'keyword','key-word'} and len(overlapping)==1 and overlapping[0][:2]==(a,b):overlapping[0][2].setdefault('keyword_annotations',[]).append(ann)
                        else:raise ValueError('Selection overlaps a saved annotation; select it for editing.')
                    else:spans.append((a,b,ann))
                    store['overrides'].append({'paragraph_id':p['paragraph_id'],'start':a,'end':b,'annotation_id':ann['id'],'term_id':term['term_id']})
                changed+=1
            p['content']=pack_content(text,spans)
    else:raise ValueError('Unknown operation.')
    if before!={p['paragraph_id']:content_text(p['content']) for p in data['paragraphs']}:raise ValueError('Original text cannot change during annotation edits.')
    save_corpus(root,data,rev)
    if not rebuild_outputs:
        return {'changed':changed,'revision':revision(root),'site_rebuilt':False}
    from textoria_rebuild import rebuild
    return {'changed':changed,**rebuild(root,site=True)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('collection',type=Path);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('state')
    for name in ['plan','edit']:sub.add_parser(name).add_argument('request',type=Path)
    serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=8766)
    args=parser.parse_args();root=args.collection.resolve()
    if args.command=='serve':
        from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
        from functools import partial
        ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(root/'site'))).serve_forever()
    elif args.command=='state':print(json.dumps({'revision':revision(root),**overview(load_corpus(root))},ensure_ascii=False))
    else:print(json.dumps((plan if args.command=='plan' else edit)(root,json.loads(args.request.read_text())),ensure_ascii=False))
if __name__=='__main__':main()
