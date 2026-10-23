"""DocuXML and standalone reader retain complete content, structure and IDs."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from textoria_build import build
from textoria_annotation_workflow import run
from textoria_corpus import load_corpus,corpus_revision
from textoria_workbench import edit,occurrences
from textoria_export_bundle import export_document
from textoria_export_docusky import validate_docuxml,metadata_rows,validate_validator_syntax
from textoria_export_reader import validate_reader

class DocumentExport(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name);source=self.project/'source.md'
        source.write_text('# 書\n\n## 卷一\n\n### 城內\n\n馬在金陵。子時。功名<&。"引文"。\n\n## 卷二\n\n馬。\n',encoding='utf-8')
        build(source,self.project,'test',label='試書',clean=False)
        self.root=self.project/'textoria-markup/collections/collection-test'
        p=self.project/'vocab.json';p.write_text(json.dumps({'entities':[{'name':'子時','types':['time']},{'name':'馬','types':['person']},{'name':'金陵','types':['place','organization']}],'keywords':['功名']}))
        run(self.root,p)

    def test_exports_current_edits_and_all_chapters_without_external_assets(self):
        d=load_corpus(self.root);horse=next(t for t in d['vocabulary']['terms'] if t['canonical_name']=='馬')
        edit(self.root,{'operation':'modify-term','scope':'all','term_id':horse['term_id'],'markup_id':'animal','confirmed':True,'revision':corpus_revision(self.root)})
        d=load_corpus(self.root);last=d['paragraphs'][-1];aid=next(a['id'] for _,_,a in occurrences(last))
        edit(self.root,{'operation':'delete','scope':'occurrence','paragraph_id':last['paragraph_id'],'annotation_id':aid,'confirmed':True,'revision':corpus_revision(self.root)})
        before=corpus_revision(self.root);result=export_document(self.root)
        self.assertEqual(corpus_revision(self.root),before);data=load_corpus(self.root)
        self.assertEqual(result['documents'],2)
        self.assertTrue(validate_reader(result['files']['html'],data))
        self.assertTrue(validate_docuxml(result['files']['docuxml'],data))
        soup=BeautifulSoup(Path(result['files']['html']).read_text(),'html.parser')
        self.assertFalse(soup.select('script[src],link[href],#addEntity,#exportHtml,#exportXml,#publishSite,#readerHelp'))
        self.assertTrue(soup.select('.reader .entity[data-markup-id="animal"]'))
        self.assertIsNone(soup.find(attrs={'data-id':aid}))
        self.assertEqual(len(soup.select('.reader article[id]')),len(data['divisions']))
        self.assertEqual(len(soup.select('.reader p[data-paragraph-number]')),len(data['paragraphs']))
        self.assertIsNotNone(soup.select_one('#entityTree'));self.assertIsNotNone(soup.select_one('.inspector'))
        xml=ET.parse(result['files']['docuxml']).getroot();self.assertEqual(xml.tag,'ThdlPrototypeExport')
        self.assertEqual(len(xml.findall('./documents/document')),2)
        self.assertTrue(xml.findall('.//LocName'));self.assertTrue(xml.findall('.//Udef_Organization'))
        self.assertTrue(xml.findall('.//Udef_Animal'))
        self.assertFalse(xml.findall('.//*[@RefId]'))
        columns,rows=metadata_rows(data)
        self.assertEqual([r['filename'] for r in rows],[e.get('filename') for e in xml.findall('./documents/document')])
        for document in xml.findall('./documents/document'):
            self.assertTrue(document.findtext('./xml_metadata/TextoriaStructure'))
        rendered=BeautifulSoup((self.root/'site/read.html').read_text(),'html.parser')
        self.assertIsNotNone(rendered.select_one('#publishSite[aria-label]'))
        self.assertEqual([b.get('id') for b in rendered.select('.header-actions > button')][:4],['addEntity','exportHtml','exportTable','exportDocuxml'])

    def test_official_validator_restrictions_and_metadata_roundtrip(self):
        result=export_document(self.root,('docuxml',))
        text=Path(result['files']['docuxml']).read_text()
        self.assertIn('&quot;',text)
        self.assertTrue(validate_validator_syntax(text))
        root=ET.fromstring(text);columns,rows=metadata_rows(load_corpus(self.root))
        for document,row in zip(root.findall('./documents/document'),rows):
            for column in columns[7:]:
                self.assertEqual(document.findtext('./xml_metadata/'+column.split('/')[1]),row[column])
        for invalid in ['<文本ID>doc-1</文本ID>','<TextoriaStructure>{"id":1}</TextoriaStructure>']:
            with self.assertRaises(ValueError):
                validate_validator_syntax('<ThdlPrototypeExport>'+invalid+'</ThdlPrototypeExport>')

    def test_custom_types_follow_docuxml_schema(self):
        result=export_document(self.root,('docuxml',));path=Path(result['files']['docuxml'])
        tree=ET.parse(path);root=tree.getroot()
        self.assertTrue(root.findall('.//Udef_Time'));self.assertFalse(root.findall('.//Time'))
        declarations=root.findall('./corpus/feature_analysis/tag')
        self.assertTrue(all(t.get('name').startswith('Udef_') for t in declarations))
        self.assertEqual({t.get('name') for t in declarations},{'Udef_Time','Udef_Organization','Udef_KeyWord'})
        declarations[0].set('name','Time');tree.write(path,encoding='utf-8')
        with self.assertRaises(ValueError):validate_docuxml(path,load_corpus(self.root))

    def test_showcase_retains_actions_and_same_tab_help(self):
        result=export_document(self.root,('html',),showcase=True)
        data=load_corpus(self.root);self.assertTrue(validate_reader(result['files']['html'],data))
        soup=BeautifulSoup(Path(result['files']['html']).read_text(),'html.parser')
        self.assertIsNotNone(soup.select_one('#publishSite'))
        self.assertFalse(soup.select('dialog,iframe'))
        link=soup.select_one('#readerHelp');self.assertIsNone(link.get('target'))
        guide_path=Path(result['files']['help']);self.assertEqual(link['href'],guide_path.name)
        guide=BeautifulSoup(guide_path.read_text(),'html.parser')
        self.assertIn('詞夾子',guide.get_text());self.assertTrue(guide.select('[data-reader-return]'))
        self.assertFalse(guide.select('script[src],link[href]'))
        self.assertIn('location.replace(url.href)',''.join(script.string or '' for script in guide.select('script')))

    def test_publish_failure_restores_existing_files(self):
        first=export_document(self.root);before={k:Path(p).read_bytes() for k,p in first['files'].items()}
        import textoria_export_bundle as exporter
        original=exporter.os.replace;calls=[]
        def fail_second(source,target):
            calls.append(str(target))
            if len(calls)==2:raise OSError('injected publication failure')
            original(source,target)
        with patch.object(exporter.os,'replace',side_effect=fail_second):
            with self.assertRaises(OSError):export_document(self.root)
        self.assertEqual(before,{k:Path(p).read_bytes() for k,p in first['files'].items()})

    def test_changed_revision_never_overwrites_export(self):
        first=export_document(self.root,('html',));path=Path(first['files']['html']);before=path.read_bytes()
        with patch('textoria_export_bundle.corpus_revision',return_value='changed'):
            with self.assertRaises(ValueError):export_document(self.root,('html',))
        self.assertEqual(path.read_bytes(),before)

if __name__=='__main__':unittest.main()
