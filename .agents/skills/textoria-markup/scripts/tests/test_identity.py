"""Identity export is usable without inferring aliases from rendered text."""
import copy
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from textoria_build import build
from textoria_annotation_workflow import run
from textoria_corpus import load_snapshot, save_corpus, validate_payload
from textoria_identity import relational_export, validate_relational_export
from textoria_annotation_uploads import read_upload


class Identity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.source = self.project/'book.md'
        self.source.write_text('# 書\n\n吳三桂與三桂。榕城就是福州。某人。\n')
        build(self.source, self.project, 'test', clean=False)
        self.root = self.project/'textoria-markup/collections/collection-test'

    def tearDown(self):
        self.temp.cleanup()

    def apply(self, entities):
        source = self.project/'input.json'
        source.write_text(json.dumps({'entities': entities}, ensure_ascii=False))
        run(self.root, source)
        return json.loads((self.root/'exports/entity.json').read_text())

    def test_alias_identity_offsets_html_and_database_foreign_keys(self):
        out = self.apply([{'name':'吳三桂','types':['person'],'aliases':['三桂']},
                          {'name':'福州','types':['place'],'aliases':['榕城']}])
        for key in ('mentions','mention_links','exclusions','overrides'):
            self.assertNotIn(key,out)
        self.assertIn('relations',out)
        from textoria_identity import relational_export
        corpus, _ = load_snapshot(self.root)
        out.update(relational_export(corpus))
        self.assertTrue(validate_relational_export(out))
        person = next(r for r in out['entities'] if r['canonical_name']=='吳三桂')
        matches = [r for r in out['mentions'] if r['surface'] in ('三桂','吳三桂')]
        self.assertEqual(len(matches), 2)
        self.assertEqual({r['entity_id'] for r in matches}, {person['entity_id']})
        names = {r['name_id']: r for r in out['names']}
        self.assertEqual({names[r['name_id']]['name_kind'] for r in matches}, {'canonical','alias'})
        paragraphs = {p['paragraph_id']: ''.join(n['text'] for n in p['content']) for p in corpus['paragraphs']}
        for m in out['mentions']:
            self.assertEqual(paragraphs[m['paragraph_id']][m['start']:m['end']], m['surface'])
        soup = BeautifulSoup((self.root/'site/read.html').read_text(), 'html.parser')
        for m in out['mentions']:
            node = soup.select_one('[data-mention-id="'+m['mention_id']+'"]')
            self.assertEqual(node['data-name-id'], m['name_id'])
            self.assertEqual(node['data-entity-id'], m['entity_id'])
            self.assertEqual(node.get_text(), m['surface'])
        # The exported relations populate normalized tables with enforced FKs.
        db=sqlite3.connect(':memory:');db.execute('PRAGMA foreign_keys=ON')
        db.executescript('CREATE TABLE entities(id TEXT PRIMARY KEY); CREATE TABLE names(id TEXT PRIMARY KEY, entity_id TEXT REFERENCES entities(id), UNIQUE(id,entity_id)); CREATE TABLE mentions(id TEXT PRIMARY KEY); CREATE TABLE links(mention_id TEXT REFERENCES mentions(id), entity_id TEXT REFERENCES entities(id), name_id TEXT, FOREIGN KEY(name_id,entity_id) REFERENCES names(id,entity_id));')
        db.executemany('INSERT INTO entities VALUES (?)',[(r['entity_id'],) for r in out['entities']])
        db.executemany('INSERT INTO names VALUES (?,?)',[(r['name_id'],r['entity_id']) for r in out['names']])
        db.executemany('INSERT INTO mentions VALUES (?)',[(r['mention_id'],) for r in out['mentions']])
        db.executemany('INSERT INTO links VALUES (?,?,?)',[(r['mention_id'],r['entity_id'],r['name_id']) for r in out['mention_links']])
        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        db.close()
        imported=read_upload(self.root/'exports/entity.json')
        self.assertNotIn('entities', imported)
        self.assertEqual(imported['terms'],out['terms'])
        bad=copy.deepcopy(out);bad['mention_links'][0]['name_id']='missing'
        with self.assertRaises(ValueError):validate_relational_export(bad)

    def test_ambiguous_names_never_export_one_resolved_person(self):
        out=self.apply([{'id':'person-a','name':'甲某','types':['person'],'aliases':['某人']},
                        {'id':'person-b','name':'乙某','types':['person'],'aliases':['某人']}])
        from textoria_identity import relational_export
        from textoria_annotation_statistics import overview
        corpus,_=load_snapshot(self.root)
        out.update(relational_export(corpus))
        self.assertTrue(validate_relational_export(out))
        mention=next(r for r in out['mentions'] if r['surface']=='某人')
        self.assertEqual(mention['identity_status'],'ambiguous')
        self.assertIsNone(mention['entity_id']);self.assertIsNone(mention['name_id'])
        links=[r for r in out['mention_links'] if r['mention_id']==mention['mention_id']]
        self.assertEqual({r['entity_id'] for r in links},{'person-a','person-b'})
        self.assertTrue(all(t['occurrences']==0 for t in overview(corpus)['terms']))

    def test_legacy_migration_is_additive_and_idempotent(self):
        self.apply([{'name':'吳三桂','types':['person'],'aliases':['三桂']}])
        c,rev=load_snapshot(self.root)
        c.pop('identity_schema_version')
        for t in c['vocabulary']['terms']:
            for a in t['aliases']:a.pop('name_id');a.pop('name_kind')
        for p in c['paragraphs']:
            for n in p['content']:
                if n.get('annotation'):n['annotation'].pop('name_id')
        baseline=copy.deepcopy(c)
        save_corpus(self.root,c,rev)
        migrated,rev=load_snapshot(self.root)
        term=migrated['vocabulary']['terms'][0]
        self.assertEqual(next(a['name_kind'] for a in term['aliases'] if a['text']=='三桂'),'unspecified')
        self.assertEqual(term['term_id'],baseline['vocabulary']['terms'][0]['term_id'])
        self.assertEqual(migrated['counts'],baseline['counts'])
        a=relational_export(migrated)
        save_corpus(self.root,migrated,rev)
        self.assertEqual(a,relational_export(load_snapshot(self.root)[0]))
        broken=copy.deepcopy(migrated)
        ann=next(n['annotation'] for p in broken['paragraphs'] for n in p['content'] if n.get('annotation'))
        ann['name_id']='wrong'
        with self.assertRaises(ValueError):validate_payload(broken)

if __name__=='__main__':unittest.main()
