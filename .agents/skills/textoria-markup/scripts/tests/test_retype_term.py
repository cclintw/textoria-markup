import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from textoria_build import build
from textoria_annotation_workflow import run
from textoria_corpus import load_corpus,corpus_revision,content_text
from textoria_workbench import edit,plan

class RetypeTerm(unittest.TestCase):
    def test_shared_identity_retype_survives_reimport_and_preserves_keyword(self):
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary);source=project/'source.md'
            source.write_text('# 書\n\n## 章\n\n馬在洛陽。\n\n馬。\n',encoding='utf-8')
            build(source,project,'test',clean=False);root=project/'textoria-markup/collections/collection-test'
            vocab=project/'names.json';vocab.write_text(json.dumps({'entities':[{'id':'horse','name':'馬','types':['person']}],'keywords':['馬']}))
            run(root,vocab);before=load_corpus(root)
            ids=[n['annotation']['id'] for p in before['paragraphs'] for n in p['content'] if n.get('annotation')]
            request={'operation':'modify-term','scope':'all','term_id':'horse','markup_id':'animal','revision':corpus_revision(root),'confirmed':True}
            self.assertEqual(plan(root,request)['affected'],2)
            result=edit(root,request);self.assertEqual(result['changed'],2)
            after=load_corpus(root)
            self.assertEqual([content_text(p['content']) for p in before['paragraphs']],[content_text(p['content']) for p in after['paragraphs']])
            horse=next(t for t in after['vocabulary']['terms'] if t['term_id']=='horse')
            self.assertEqual(horse['markup_ids'],['animal'])
            self.assertEqual(horse['aliases'],next(t for t in before['vocabulary']['terms'] if t['term_id']=='horse')['aliases'])
            for p in after['paragraphs']:
                for n in p['content']:
                    if not n.get('annotation'):continue
                    a=n['annotation'];self.assertEqual(a['markup_ids'],['animal']);self.assertFalse(a['conflict'])
                    self.assertTrue(a['keyword_annotations']);self.assertEqual(a['keyword_annotations'][0]['markup_id'],'key-word')
            self.assertEqual(ids,[n['annotation']['id'] for p in after['paragraphs'] for n in p['content'] if n.get('annotation')])
            run(root,vocab)
            self.assertEqual(next(t for t in load_corpus(root)['vocabulary']['terms'] if t['term_id']=='horse')['markup_ids'],['animal'])
            exported=json.loads((root/'exports/entity.json').read_text())
            self.assertEqual(next(t for t in exported['terms'] if t['term_id']=='horse')['markup_ids'],['animal'])

    def test_alternative_identity_is_retained_and_scope_is_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary);source=project/'source.md';source.write_text('# 書\n\n馬。\n',encoding='utf-8')
            build(source,project,'test',clean=False);root=project/'textoria-markup/collections/collection-test'
            vocab=project/'names.json';vocab.write_text(json.dumps({'entities':[{'id':'horse-a','name':'馬','types':['person']},{'id':'horse-b','name':'馬','types':['animal']}]}))
            run(root,vocab);revision=corpus_revision(root)
            request={'operation':'modify-term','scope':'occurrence','term_id':'horse-a','markup_id':'animal','revision':revision,'confirmed':True}
            with self.assertRaises(ValueError):edit(root,request)
            self.assertEqual(corpus_revision(root),revision)
            request['scope']='all';edit(root,request)
            a=next(n['annotation'] for p in load_corpus(root)['paragraphs'] for n in p['content'] if n.get('annotation'))
            self.assertEqual(a['markup_ids'],['animal']);self.assertTrue(a['conflict']);self.assertTrue(a['identity_conflict'])
            self.assertEqual([{k:v for k,v in ref.items() if k!='name_id'} for ref in a['term_alternatives']],[{'term_id':'horse-b','markup_id':'animal'}])
        self.assertTrue(a['term_alternatives'][0]['name_id'].startswith('name-'))

if __name__=='__main__':unittest.main()
