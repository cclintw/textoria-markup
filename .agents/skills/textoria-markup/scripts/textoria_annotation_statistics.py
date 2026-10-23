"""Small, derived counts for the reader and formal vocabulary exports."""
from collections import Counter
import copy
from textoria_annotation import iter_annotations


def overview(data):
    counts=Counter();terms=Counter();total=0
    for p in data['paragraphs']:
        for node in p['content']:
            if not node.get('annotation'):continue
            for ann in iter_annotations(node['annotation']):
                total+=1;counts.update(ann.get('markup_ids',[ann.get('markup_id',ann.get('type'))]))
                for tid in {ann.get('term_id'),*(a['term_id'] for a in ann.get('term_alternatives',[]))}:
                    if tid:terms[tid]+=1
    return {'types':data.get('annotation_profile',{}).get('types',[]),
            'terms':[{**copy.deepcopy(t),'authority_id':t['term_id'],'occurrences':terms[t['term_id']]} for t in data.get('vocabulary',{}).get('terms',[])],
            'counts':dict(counts),'total_annotations':total,'collection_id':data['collection']['collection_id']}


def statistics(root):
    from textoria_corpus import load_corpus
    return overview(load_corpus(root))
