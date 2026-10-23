"""Behavioral tests: real source -> corpus -> annotation -> reader -> dialogue edit."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from textoria_build import build
from textoria_corpus import load_corpus,corpus_revision,content_text,save_corpus
from textoria_annotation_workflow import run
from textoria_workbench import edit
from textoria_rule_engine import matches,validate_rule
from textoria_rebuild import rebuild

class Markup(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.project=Path(self.temp.name);self.source=self.project/'source.txt'
        self.source.write_text('# 第一回\n\n金陵有寶玉，名曰黛玉，授知府一職。功名。\n\n金陵又有寶玉。\n',encoding='utf-8')
        build(self.source,self.project,'test',clean=False);self.root=self.project/'textoria-markup/collections/collection-test'
    def tearDown(self):self.temp.cleanup()
    def upload(self,data,name='input.json'):
        p=self.project/name;p.write_text(json.dumps(data,ensure_ascii=False));return run(self.root,p)
    def test_single_source_and_shared_ui(self):
        self.assertFalse((self.root/'intermediate').exists());self.assertFalse((self.root/'annotation').exists());self.assertFalse((self.root/'clean').exists())
        self.assertTrue((self.root/'site/assets/help.html').is_file());self.assertFalse((self.root/'exports').exists())
        self.assertIn('id="addEntity"',(self.root/'site/read.html').read_text())
    def test_structure_rebuild_defers_exports_until_annotation_or_explicit_export(self):
        before=corpus_revision(self.root)
        result=rebuild(self.root,site=True)
        self.assertFalse((self.root/'exports').exists())
        self.assertEqual(result['exports'],{})
        rebuild(self.root,exports=True)
        self.assertTrue((self.root/'exports/entity.json').is_file())
        self.assertEqual(corpus_revision(self.root),before)

    def test_unmatched_uploaded_terms_still_export_and_other_exports_survive(self):
        self.upload({'entities':[{'name':'不存在的寺','types':['place']}]})
        folder=self.root/'exports';extra=folder/'notes.txt';extra.write_text('keep')
        self.assertEqual(load_corpus(self.root)['counts']['annotations'],0)
        vocabulary=json.loads((folder/'entity.json').read_text())
        self.assertTrue(vocabulary['terms'])
        rebuild(self.root)
        self.assertEqual(extra.read_text(),'keep')

    def test_external_conflicts_keywords_rules_and_rerun(self):
        original=[content_text(p['content']) for p in load_corpus(self.root)['paragraphs']]
        result=self.upload({'entities':[{'name':'寶玉','types':['person']},{'name':'寶玉','types':['artifact']},{'name':'金陵','types':['place']}],
            'keywords':['功名'],'rules':[{'id':'r1','kind':'between','before':'名曰','after':'，','type':'person','min_length':2,'max_length':6},{'id':'r2','kind':'regex','pattern':'授([^。]+?)一職','group':1,'type':'office'}]})
        data=load_corpus(self.root);self.assertEqual(original,[content_text(p['content']) for p in data['paragraphs']])
        hits=[(n['text'],n['annotation']) for p in data['paragraphs'] for n in p['content'] if n.get('annotation')]
        baoyu=next(a for text,a in hits if text=='寶玉');self.assertEqual(set(baoyu['markup_ids']),{'person','artifact'});self.assertTrue(baoyu['conflict'])
        self.assertTrue(any(t=='黛玉' for t,a in hits));self.assertTrue(any(t=='知府' for t,a in hits));self.assertTrue(any(a['markup_id']=='key-word' for t,a in hits))
        self.assertEqual(run(self.root,rerun=True)['added'],0)
        exported=json.loads((self.root/'exports/entity.json').read_text());self.assertEqual(len(exported['rules']),2)
    def test_formal_vocabulary_wins_over_new_source(self):
        self.upload({'entities':[{'name':'金陵','types':['place']}]})
        self.upload({'entities':[{'name':'金陵','types':['person']}]},'other.json')
        data=load_corpus(self.root);self.assertEqual(next(t for t in data['vocabulary']['terms'] if t['canonical_name']=='金陵')['markup_ids'],['place'])
        self.assertTrue(data['annotation_state']['source_differences'])
    def test_exact_delete_does_not_return_on_rerun(self):
        self.upload({'entities':[{'name':'金陵','types':['place']}]});data=load_corpus(self.root)
        p=next(p for p in data['paragraphs'] if any(n.get('annotation') for n in p['content']));ann=next(n['annotation'] for n in p['content'] if n.get('annotation'))
        request={'operation':'delete','scope':'occurrence','paragraph_id':p['paragraph_id'],'annotation_id':ann['id'],'confirmed':True,'revision':corpus_revision(self.root)}
        edit(self.root,request);remaining=load_corpus(self.root)['counts']['annotations'];self.assertEqual(remaining,1)
        run(self.root,rerun=True);self.assertEqual(load_corpus(self.root)['counts']['annotations'],remaining)
        with self.assertRaises(ValueError):edit(self.root,request)
    def test_edits_require_confirmation_and_preserve_text(self):
        d=load_corpus(self.root);p=d['paragraphs'][0];text=content_text(p['content']);start=text.index('金陵')
        request={'operation':'save','scope':'occurrence','paragraph_id':p['paragraph_id'],'start':start,'end':start+2,'text':'金陵','markup_id':'place','revision':corpus_revision(self.root)}
        with self.assertRaises(ValueError):edit(self.root,request)
        request['confirmed']=True;edit(self.root,request)
        self.assertEqual(content_text(load_corpus(self.root)['paragraphs'][0]['content']),text)
    def test_failed_publication_retains_previous_site(self):
        from unittest.mock import patch
        old=(self.root/'site/read.html').read_bytes()
        with patch('textoria_build_site.build_static_site',side_effect=RuntimeError('injected renderer error')):
            with self.assertRaises(RuntimeError):rebuild(self.root,site=True)
        self.assertEqual((self.root/'site/read.html').read_bytes(),old)
    def test_undo_and_formal_json_roundtrip(self):
        self.upload({'entities':[{'name':'金陵','types':['place']}]})
        prior=load_corpus(self.root)['counts']['annotations']
        p=load_corpus(self.root)['paragraphs'][0];ann=next(n['annotation'] for n in p['content'] if n.get('annotation'))
        edit(self.root,{'operation':'delete','scope':'occurrence','paragraph_id':p['paragraph_id'],'annotation_id':ann['id'],'confirmed':True,'revision':corpus_revision(self.root)})
        edit(self.root,{'operation':'undo','confirmed':True,'revision':corpus_revision(self.root)})
        self.assertEqual(load_corpus(self.root)['counts']['annotations'],prior)
        original=load_corpus(self.root)['vocabulary']
        exported=json.loads((self.root/'exports/entity.json').read_text())
        second=self.project/'second';second.mkdir();build(self.source,second,'test',clean=False)
        other=second/'textoria-markup/collections/collection-test';f=self.project/'formal.json';f.write_text(json.dumps(exported));run(other,f)
        self.assertEqual(load_corpus(other)['vocabulary'],original)

    def test_epub_is_optional_derived_export(self):
        import zipfile
        from textoria_build_epub import build_epub
        from textoria_common import ensure_dirs
        from textoria_corpus import to_render_data
        before=corpus_revision(self.root)
        result=build_epub(ensure_dirs(self.root),to_render_data(load_corpus(self.root)))
        with zipfile.ZipFile(result['epub']) as archive:
            self.assertEqual(archive.namelist()[0],'mimetype')
            self.assertIn('OEBPS/content.opf',archive.namelist())
        self.assertEqual(corpus_revision(self.root),before)

    def test_csv_aliases_new_types_and_partial_overlap_reporting(self):
        p=self.project/'entities.csv';p.write_text('name,type,alias\n寶玉,人物,\n金陵,地點,\n金陵有,新類型,\n馬,animal,\n')
        run(self.root,p)
        data=load_corpus(self.root)
        self.assertTrue(any(t['label']=='新類型' for t in data['annotation_profile']['types']))
        self.assertTrue(data['annotation_state']['overlaps'])
        self.assertEqual(next(t['label'] for t in data['annotation_profile']['types'] if t['markup_id']=='animal'),'動物')

    def test_invalid_rule_never_writes_corpus(self):
        before=corpus_revision(self.root)
        with self.assertRaises(ValueError):self.upload({'rules':[{'id':'bad','kind':'regex','pattern':'(a+)+$','type':'person'}]})
        self.assertEqual(corpus_revision(self.root),before)

if __name__=='__main__':unittest.main()
