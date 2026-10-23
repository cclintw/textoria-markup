"""Collection selection must precede any persistent import."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from textoria_intake import plan


class Intake(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.source = self.project / 'source.md'
        self.source.write_text('# 原文\n洛陽。\n', encoding='utf-8')

    def test_undecided_does_not_create_data(self):
        self.assertEqual(plan(self.source, self.project)['status'], 'needs_collection_choice')
        self.assertFalse((self.project / 'textoria-markup').exists())
        with self.assertRaises(ValueError):
            plan(self.source, self.project, slug='test')

    def test_existing_selection_preserves_corpus(self):
        root = self.project / 'textoria-markup/collections/collection-test'
        root.mkdir(parents=True)
        corpus = root / 'corpus.json'
        corpus.write_text(json.dumps({'collection': {'collection_id': root.name,
                                                     'title': '既有文本'}, 'documents': []}))
        before = corpus.read_bytes()
        result = plan(self.source, self.project, mode='existing', slug='test')
        self.assertEqual(result['target'], str(root.resolve()))
        self.assertEqual(corpus.read_bytes(), before)
        with self.assertRaises(ValueError):
            plan(self.source, self.project, mode='new', slug='test')
        with self.assertRaises(ValueError):
            plan(self.source, self.project, mode='existing', slug='missing')

    def test_new_target_is_only_a_plan(self):
        result = plan(self.source, self.project, mode='new', slug='luoyang')
        self.assertEqual(result['status'], 'target_resolved')
        self.assertFalse(Path(result['target']).exists())
        with self.assertRaises(ValueError):
            plan(self.source, self.project, mode='new', slug='../escape')


if __name__ == '__main__':
    unittest.main()
