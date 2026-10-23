"""Persistent Markdown review stage and confirmed structure commit."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from textoria_prepare import prepare
from textoria_build import build
from textoria_corpus import load_corpus, content_text

class Preparation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name)

    def test_all_supported_sources_have_markdown_working_copy(self):
        cases=[('a.md','# 卷一\n\n神①，保留異體字。\n',None),
               ('b.txt','洛陽。',None),
               ('c.html','<h1>卷一</h1><p>洛陽。</p>',None),
               ('d.csv','body\n洛陽。\n','body')]
        for i,(name,text,column) in enumerate(cases):
            with self.subTest(name=name):
                source=self.project/name;source.write_text(text,encoding='utf-8')
                result=prepare(source,self.project,f'test-{i}',text_column=column)
                root=Path(result['collection']);clean=Path(result['clean_file'])
                self.assertEqual(clean.suffix,'.md')
                self.assertEqual((root/'uploads'/name).read_bytes(),source.read_bytes())
                self.assertIn('洛陽' if i else '神①',clean.read_text(encoding='utf-8'))
                self.assertFalse((root/'corpus.json').exists())
                self.assertFalse((root/'site').exists())
                build(source,self.project,f'test-{i}',clean=False,site=False,prepared_md=clean,prepared_sha256=result['prepared_sha256'])
                self.assertTrue((root/'corpus.json').exists())
                self.assertFalse((root/'exports').exists())

    def test_user_edit_survives_and_latest_markdown_drives_structure(self):
        source=self.project/'source.md';source.write_text('# 卷一\n\n原文。\n',encoding='utf-8')
        result=prepare(source,self.project,'test');root=Path(result['collection']);clean=Path(result['clean_file'])
        clean.write_text('# 卷一\n\n## 城內\n\n### 永寧寺\n\n原文。\n',encoding='utf-8')
        revised=clean.read_bytes();sha=hashlib.sha256(revised).hexdigest()
        with self.assertRaises(ValueError):prepare(source,self.project,'test',mode='existing')
        self.assertEqual(clean.read_bytes(),revised)
        with self.assertRaises(ValueError):
            build(source,self.project,'test',clean=False,prepared_md=clean,prepared_sha256=result['prepared_sha256'])
        self.assertFalse((root/'corpus.json').exists())
        build(source,self.project,'test',clean=False,prepared_md=clean,prepared_sha256=sha)
        corpus=load_corpus(root)
        self.assertIn('永寧寺',[d['title'] for d in corpus['divisions']])
        self.assertEqual([content_text(p['content']) for p in corpus['paragraphs']],['原文。'])
        self.assertEqual(corpus['source_preparation']['prepared_sha256'],sha)
        self.assertEqual(clean.read_bytes(),revised)
        self.assertEqual((root/'uploads/source.md').read_bytes(),source.read_bytes())

    def test_invalid_input_never_creates_collection(self):
        source=self.project/'data.bin';source.write_bytes(b'\x00\x01')
        with self.assertRaises(ValueError):prepare(source,self.project,'bad')
        self.assertFalse((self.project/'textoria-markup').exists())

if __name__=='__main__':unittest.main()
