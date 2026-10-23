"""Empty chapter display follows the tree without changing canonical ownership."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from textoria_build import build
from textoria_annotation_workflow import run
from textoria_corpus import load_corpus, corpus_revision
from textoria_reader_sections import reader_sections
from textoria_rebuild import rebuild


class EmptyChapter(unittest.TestCase):
    def test_recursive_display_metadata_and_own_text_behavior(self):
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary);source=project/'source.md'
            source.write_text('# 書\n\n## 卷一\n\n### 無文小節\n\n### 城內\n\n#### 永寧寺\n\n洛陽有寺。\n\n#### 建中寺\n\n另一寺。\n\n## 卷二\n\n卷二正文。\n\n### 子節\n\n子節正文。\n\n## 無內容卷\n',encoding='utf-8')
            build(source,project,'test',clean=False)
            root=project/'textoria-markup/collections/collection-test'
            vocab=project/'vocab.json';vocab.write_text(json.dumps({'entities':[{'name':'洛陽','types':['place']}]}))
            run(root,vocab)
            corpus=load_corpus(root);bytitle={d['title']:d for d in corpus['divisions']}
            parent=bytitle['卷一'];temple=bytitle['永寧寺'];para=next(p for p in corpus['paragraphs'] if p['division_id']==temple['division_id'])
            self.assertEqual([d['title'] for d in reader_sections(corpus,parent['division_id'])],['卷一','城內','永寧寺'])
            soup=BeautifulSoup((root/'site/read'/f"{parent['division_id']}.html").read_text(),'html.parser')
            self.assertEqual([h.get_text() for h in soup.select('.reader article h2')],['卷一','城內','永寧寺'])
            displayed=soup.select('p[data-paragraph-number]')
            self.assertEqual([p['id'] for p in displayed],[para['paragraph_id']])
            self.assertEqual(displayed[0].find_parent('article')['id'],temple['division_id'])
            metadata=json.loads(soup.select_one('#annotationPage').string)
            self.assertEqual(metadata['division_id'],parent['division_id'])
            self.assertEqual([p['paragraph_id'] for p in metadata['paragraphs']],[para['paragraph_id']])
            self.assertEqual(metadata['paragraphs'][0]['division_id'],temple['division_id'])
            self.assertTrue(displayed[0].select('.entity[data-id]'))
            # Parents with their own text never append child text.
            own=bytitle['卷二'];own_soup=BeautifulSoup((root/'site/read'/f"{own['division_id']}.html").read_text(),'html.parser')
            self.assertEqual([p.get_text() for p in own_soup.select('p[data-paragraph-number]')],['卷二正文。'])
            self.assertEqual([d['title'] for d in reader_sections(corpus,bytitle['無文小節']['division_id'])],['無文小節'])
            self.assertEqual([d['title'] for d in reader_sections(corpus,bytitle['無內容卷']['division_id'])],['無內容卷'])
            before=corpus_revision(root);rebuild(root,site=True);self.assertEqual(corpus_revision(root),before)

if __name__=='__main__':unittest.main()
