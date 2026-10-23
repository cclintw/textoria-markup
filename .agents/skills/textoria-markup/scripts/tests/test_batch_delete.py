import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from textoria_build import build
from textoria_annotation_workflow import run
from textoria_workbench import edit,plan,occurrences
from textoria_corpus import load_corpus,corpus_revision,content_text

class BatchDelete(unittest.TestCase):
    def test_exact_batch_preserves_protected_mentions_keywords_and_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary);source=project/'source.md'
            source.write_text('# 書\n\n## 章\n\n甲與乙。《甲》。甲。\n',encoding='utf-8')
            build(source,project,'test',clean=False);root=project/'textoria-markup/collections/collection-test'
            vocab=project/'vocab.json';vocab.write_text(json.dumps({'entities':[{'name':'甲','types':['person']},{'name':'乙','types':['person']}],'keywords':['甲']}))
            run(root,vocab);before=load_corpus(root);p=before['paragraphs'][0]
            rows=[(start,ann) for start,end,ann in occurrences(p) if ann['markup_id']=='person']
            ids=[ann['id'] for start,ann in rows if start in (0,8)]
            self.assertEqual(len(ids),2)
            request={'operation':'delete','scope':'all','annotation_ids':ids,'confirmed':True,'revision':corpus_revision(root)}
            self.assertEqual(plan(root,request)['affected'],2)
            bad={**request,'annotation_ids':ids+['missing']}
            with self.assertRaises(ValueError):edit(root,bad)
            self.assertEqual(corpus_revision(root),request['revision'])
            result=edit(root,request);self.assertEqual(result['changed'],2)
            after=load_corpus(root)
            self.assertEqual(content_text(after['paragraphs'][0]['content']),content_text(p['content']))
            remaining=[ann for para in after['paragraphs'] for a,b,ann in occurrences(para)]
            self.assertEqual(sum(a['markup_id']=='person' for a in remaining),2)
            self.assertEqual(sum(a['markup_id']=='key-word' for a in remaining),3)
            self.assertTrue(all(a['id'] not in ids for a in remaining))
            run(root,rerun=True)
            self.assertEqual(sum(ann['markup_id']=='person' for para in load_corpus(root)['paragraphs'] for a,b,ann in occurrences(para)),2)

if __name__=='__main__':unittest.main()
