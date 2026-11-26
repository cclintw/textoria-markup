"""External input -> deterministic direct annotation. No AI extraction/candidate gate."""
from __future__ import annotations
import copy
from collections import defaultdict
from textoria_annotation import digest,ensure_type,normalize_alias,scope_matches,iter_annotations,pack_content,markup_ids
from textoria_corpus import content_text,load_corpus,load_snapshot,corpus_revision,save_corpus
from textoria_entity_sources import entity_metadata, merge_entity_metadata
from textoria_reference_tables import compile_reference, project_tables, read_working_tables
from textoria_rule_engine import validate_rule,matches as rule_matches


def state(data):return data.setdefault('annotation_state',{'rules':[],'imports':[],'exclusions':[],'overlaps':[],'overrides':[]})


def aliases_for(item,name,source):
    forms=[name,*item.get('aliases',[])]
    result=[]
    for form in forms:
        alias=copy.deepcopy(form) if isinstance(form,dict) else {'text':form,'match_policy':item.get('match_policy','exact'),'scope':item.get('scope',{}),'sources':[source]}
        alias.setdefault('name_kind','canonical' if alias['text']==name else 'alias')
        result.append(normalize_alias(alias))
    return result


def merge_inputs(data,incoming,source):
    store=state(data);official={t['term_id'] for t in data['vocabulary']['terms']};terms=data['vocabulary']['terms'];byid={t['term_id']:t for t in terms}
    for spec in incoming.get('types',[]):
        if not isinstance(spec,dict) or not spec.get('markup_id'):raise ValueError('Invalid imported type.')
        if not any(x['markup_id']==spec['markup_id'] for x in data['annotation_profile']['types']):data['annotation_profile']['types'].append(copy.deepcopy(spec))
    entries=[]
    for item in incoming.get('entities',[]):
        if not isinstance(item,dict) or not isinstance(item.get('name'),str) or not item['name'].strip():raise ValueError('Entity needs a name.')
        kinds=item.get('types') or ([item['type']] if item.get('type') else [])
        if not isinstance(kinds,list) or not kinds or any(not isinstance(k,str) or not k for k in kinds):raise ValueError('Entity needs types.')
        name=item['name'].strip();ids=list(dict.fromkeys(ensure_type(data,k) for k in kinds))
        entries.append({'term_id':item.get('id') or item.get('term_id'),'canonical_name':name,'markup_ids':ids,'aliases':aliases_for(item,name,source),'sources':[source],**entity_metadata({**item,'markup_ids':ids})})
    for word in incoming.get('keywords',[]):
        if not isinstance(word,str) or not word.strip():raise ValueError('Keyword must be a nonempty string.')
        word=word.strip();entries.append({'canonical_name':word,'markup_ids':[ensure_type(data,'key-word')],'aliases':[normalize_alias({'text':word,'match_policy':'exact','sources':[source]})],'sources':[source]})
    for t in incoming.get('terms',[]):
        row=copy.deepcopy(t)
        if not isinstance(row,dict) or not row.get('canonical_name') or not row.get('aliases'):raise ValueError('Invalid formal vocabulary term.')
        row['markup_ids']=[ensure_type(data,m) for m in row.get('markup_ids',[row['markup_id']])];entries.append(row)
    differences=[]
    for row in entries:
        ids=row['markup_ids'];keyword=ids[0] in {'keyword','key-word'}
        explicit=row.get('term_id');same=next((t for t in terms if t['canonical_name']==row['canonical_name'] and (t['markup_id'] in {'keyword','key-word'})==keyword),None)
        prior=byid.get(explicit) if explicit else same
        if prior:
            if prior['term_id'] in official:
                # The formal vocabulary's identity/types/scopes win. New conflicting
                # evidence is recorded, not silently substituted on repeated runs.
                if prior['canonical_name']!=row['canonical_name'] or prior.get('markup_ids',[prior['markup_id']])!=ids:differences.append({'term_id':prior['term_id'],'source':source,'incoming_types':ids,'incoming_name':row['canonical_name']})
                else:merge_entity_metadata(prior,entity_metadata(row),keep_location=True)
                for a in row['aliases']:
                    if not any(old['text']==a['text'] for old in prior['aliases']):prior['aliases'].append(a)
            else:
                merge_entity_metadata(prior,entity_metadata(row),keep_location=False)
                prior['markup_ids']=list(dict.fromkeys([*prior['markup_ids'],*ids]));prior['conflict']=len(prior['markup_ids'])>1
                for a in row['aliases']:
                    if a not in prior['aliases']:prior['aliases'].append(a)
                prior['sources']=list(dict.fromkeys([*prior.get('sources',[]),source]))
        else:
            tid=explicit or 'term-'+digest([row['canonical_name'],keyword])[:20]
            if tid in byid:raise ValueError('Conflicting term ID.')
            term={**row,'term_id':tid,'markup_id':ids[0],'markup_ids':ids,'conflict':len(ids)>1};term.pop('id',None)
            term['aliases']=[normalize_alias(a) for a in term['aliases']]
            terms.append(term);byid[tid]=term
    relations=store.setdefault('relations',[])
    for row in incoming.get('relations',[]):
        if not isinstance(row,dict) or row.get('subject_id') not in byid or row.get('object_id') not in byid or not isinstance(row.get('type'),str) or not row['type'].strip():
            raise ValueError('Relation needs a type and two known term IDs.')
        if row not in relations:relations.append(copy.deepcopy(row))
    known={r['id']:r for r in store['rules']};official_rules=set(known)
    for original in incoming.get('rules',[]):
        rule=copy.deepcopy(original);rule['type']=ensure_type(data,rule.get('type',''));validate_rule(rule)
        if 'term_id' in rule and rule['type'] not in byid.get(rule['term_id'],{}).get('markup_ids',[]):
            raise ValueError('Rule term_id must identify a term of the target type.')
        if rule['id'] in known:
            if known[rule['id']]!=rule:
                if rule['id'] not in official_rules:raise ValueError('One upload contains conflicting rules with the same ID.')
                differences.append({'rule_id':rule['id'],'source':source,'incoming_rule':rule})
        else:store['rules'].append(rule);known[rule['id']]=rule
    for key in ['exclusions','overrides']:
        for row in incoming.get(key,[]):
            if not isinstance(row,dict):raise ValueError(key+' entries must be objects.')
            if row not in store[key]:store[key].append(copy.deepcopy(row))
    store.setdefault('source_differences',[]).extend(differences)
    return differences


def term_for_rule(data,rule,hit,p):
    # Context-derived names stay scoped to the actual matching paragraph; the
    # reusable rule, not a global literal alias, governs future occurrences.
    mid=rule['type'];terms=data['vocabulary']['terms']
    term=next((t for t in terms if t['term_id']==rule['term_id']),None) if 'term_id' in rule else next(
        (t for t in terms if t['canonical_name']==hit and mid in t.get('markup_ids',[t['markup_id']])),None)
    if 'term_id' in rule and term is None:raise ValueError('Rule target term does not exist.')
    alias={'text':hit,'match_policy':'contextual','scope':{'paragraph_ids':[p['paragraph_id']]},'sources':['rule:'+rule['id']]}
    if term:
        if not any(a['text']==hit and scope_matches(a,p) for a in term['aliases']):term['aliases'].append(alias)
        return term
    tid='term-'+digest([hit,mid])[:20]
    term={'term_id':tid,'canonical_name':hit,'markup_id':mid,'markup_ids':[mid],'conflict':False,'aliases':[alias],'sources':['rule:'+rule['id']]};terms.append(term);return term


def make_annotation(data,terms,p,start,end):
    unique={t['term_id']:t for t in terms};terms=list(unique.values());types=list(dict.fromkeys(m for t in terms for m in t.get('markup_ids',[t['markup_id']])))
    ann={'id':'m-'+digest([data['collection']['collection_id'],p['paragraph_id'],start,end,sorted(unique)])[:24],
         'markup_id':types[0],'markup_ids':types,'term_id':terms[0]['term_id'],'attributes':{},'conflict':len(types)>1 or len(terms)>1 and len(types)==1}
    if len(terms)>1:
        ann['term_alternatives']=[{'term_id':t['term_id'],'markup_id':t['markup_id']} for t in terms[1:]]
        if len(types)==1:ann['identity_conflict']=True
    if ann['conflict']:ann['conflict_note']='保留上傳來源的不同類型或身分，尚未裁決。'
    return ann


def annotate(data,scope=None):
    store=state(data);added=0;overlaps=[];rules=store['rules']
    # Rule extraction first registers only names actually present in matching contexts.
    rule_hits=defaultdict(list)
    for p in data['paragraphs']:
        if scope and not scope_matches({'scope':scope},p):continue
        text=content_text(p['content'])
        for rule in rules:
            if rule.get('enabled',True):
                for a,b in rule_matches(rule,text,p):rule_hits[p['paragraph_id']].append((a,b,term_for_rule(data,rule,text[a:b],p)))
    for p in data['paragraphs']:
        if scope and not scope_matches({'scope':scope},p):continue
        text=content_text(p['content']);found=defaultdict(list);scoped=defaultdict(set)
        for term in data['vocabulary']['terms']:
            for alias in term['aliases']:
                if not scope_matches(alias,p):continue
                if alias.get('sources') and all(s.startswith('rule:') for s in alias['sources']):
                    continue
                a=text.find(alias['text'])
                while a>=0:
                    span=(a,a+len(alias['text']))
                    found[span].append(term)
                    if alias.get('name_kind')=='contextual_form' and alias.get('scope'):
                        scoped[span].add(term['term_id'])
                    a=text.find(alias['text'],a+1)
        for a,b,t in rule_hits[p['paragraph_id']]:
            found[(a,b)].append(t)
            scoped[(a,b)].add(t['term_id'])
        spans=[];cursor=0
        for n in p['content']:
            end=cursor+len(n['text'])
            if n.get('annotation'):spans.append((cursor,end,copy.deepcopy(n['annotation'])))
            cursor=end
        for (a,b),terms in sorted(found.items(),key=lambda row:(row[0][0],-(row[0][1]-row[0][0]))):
            terms=list({t['term_id']:t for t in terms}.values())
            terms=[t for t in terms if not any(e.get('paragraph_id')==p['paragraph_id'] and e.get('start')==a and e.get('end')==b and (not e.get('term_id') or e['term_id']==t['term_id']) for e in store['exclusions'])]
            override=next((o for o in reversed(store['overrides']) if o.get('paragraph_id')==p['paragraph_id'] and o.get('start')==a and o.get('end')==b),None)
            if override:terms=[t for t in terms if t['term_id']==override.get('term_id') or t['markup_id'] in {'keyword','key-word'}]
            elif any(t['term_id'] in scoped[(a,b)] and t['markup_id'] not in {'keyword','key-word'} for t in terms):
                terms=[t for t in terms if t['term_id'] in scoped[(a,b)] or t['markup_id'] in {'keyword','key-word'}]
            if not terms:continue
            same=next((span for span in spans if span[:2]==(a,b)),None)
            entity=[t for t in terms if t['markup_id'] not in {'keyword','key-word'}];keywords=[t for t in terms if t['markup_id'] in {'keyword','key-word'}]
            if same:
                known={t.get('term_id') for t in iter_annotations(same[2])}
                # Existing saved annotations always win over reruns; only a new
                # same-span keyword membership can be added without replacement.
                for term in keywords:
                    if term['term_id'] not in known:same[2].setdefault('keyword_annotations',[]).append(make_annotation(data,[term],p,a,b));added+=1
                continue
            if any(a<end and b>start for start,end,_ in spans):overlaps.append({'paragraph_id':p['paragraph_id'],'start':a,'end':b,'text':text[a:b],'term_ids':[t['term_id'] for t in terms]});continue
            ann=make_annotation(data,entity or keywords[:1],p,a,b)
            extra=keywords if entity else keywords[1:]
            if extra:ann['keyword_annotations']=[make_annotation(data,[t],p,a,b) for t in extra]
            spans.append((a,b,ann));added+=1+len(extra)
        p['content']=pack_content(text,spans)
    store['overlaps']=overlaps
    return {'added':added,'overlaps':len(overlaps)}


def install_reference(data, reference):
    data['vocabulary']['terms']=reference['terms']
    store=state(data)
    store.update(relations=reference['relations'],rules=reference['rules'])


def matching_signature(reference):
    terms={}
    for term in reference['terms']:
        forms={(a['text'],a['match_policy'],digest(a['scope']),a.get('name_kind')=='contextual_form',
                bool(a.get('sources')) and all(s.startswith('rule:') for s in a['sources']))
               for a in term['aliases']}
        terms[term['term_id']]=(term['markup_ids'],forms)
    return terms, reference['rules']


def clear_automatic_annotations(data):
    protected={row.get('annotation_id') for row in state(data).get('overrides',[])}
    for paragraph in data['paragraphs']:
        spans=[];start=0
        for node in paragraph['content']:
            end=start+len(node['text'])
            if node.get('annotation'):
                kept=[]
                for ann in iter_annotations(node['annotation']):
                    if ann.get('user_confirmed') or ann['id'] in protected or 'markup_id' not in ann:
                        kept.append({k: v for k,v in ann.items() if k!='keyword_annotations'})
                if kept:
                    if len(kept)>1:kept[0]['keyword_annotations']=kept[1:]
                    spans.append((start,end,kept[0]))
            start=end
        paragraph['content']=pack_content(content_text(paragraph['content']),spans)


def run(root,source=None,normalized=None,keywords=False,scope=None,rerun=False):
    data,rev=load_snapshot(root);before={p['paragraph_id']:content_text(p['content']) for p in data['paragraphs']}
    tables,reference_rev=read_working_tables(root)
    if tables is not None:
        baseline=compile_reference(data,project_tables(data))
        updated=compile_reference(data,tables)
        matching_changed=matching_signature(baseline)!=matching_signature(updated)
        if matching_changed:
            if scope:raise ValueError('工作詞表的比對條件已變更，請確認整個文集的重跑範圍。')
            clear_automatic_annotations(data)
        install_reference(data,updated)
        if matching_changed:
            from textoria_corpus import validate_payload
            from textoria_identity import synchronize_names
            try:
                synchronize_names(data)
                validate_payload(data)
            except (KeyError,ValueError) as exc:
                raise ValueError(f'工作詞表的變更與已確認的標註有衝突：{exc}') from exc
    receipt=None
    if source:
        from textoria_annotation_uploads import prepare_upload
        incoming,receipt=prepare_upload(root,source,normalized,'keywords' if keywords else 'auto')
        merge_inputs(data,incoming,str(receipt['file']))
    elif not rerun:raise ValueError('Provide an external source, or explicitly request --rerun.')
    install_reference(data,compile_reference(data,project_tables(data)))
    result=annotate(data,scope)
    if receipt:
        receipt.update(result);state(data)['imports'].append(receipt)
    assert before=={p['paragraph_id']:content_text(p['content']) for p in data['paragraphs']}
    state(data)['reference_input_revision']=reference_rev
    save_corpus(root,data,rev,expected_reference_revision=reference_rev)
    from textoria_rebuild import rebuild
    result.update(rebuild(root,site=True));return result
