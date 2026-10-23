import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from textoria_utf8_converter import detect_encoding, decode_to_text, inspect_source_encoding, normalize_decoded_text

class Encoding(unittest.TestCase):
    def test_bom_and_lossless_conversion(self):
        text = '洛陽伽藍記：①神\n'
        for encoding in ('utf-8', 'utf-8-sig', 'utf-16', 'utf-32'):
            raw = text.encode(encoding)
            detected, _ = detect_encoding(raw)
            self.assertEqual(normalize_decoded_text(decode_to_text(raw, detected)), text)
        raw = '洛陽伽藍記'.encode('big5')
        self.assertEqual(decode_to_text(raw, 'big5'), '洛陽伽藍記')

    def test_inspection_keeps_original_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'text.md'
            raw = '洛陽'.encode('utf-16')
            path.write_bytes(raw)
            self.assertTrue(inspect_source_encoding(path)['conversion_to_utf8_needed'])
            self.assertEqual(path.read_bytes(), raw)

    def test_uncertain_or_invalid_decoding_stops(self):
        with self.assertRaises(ValueError):
            decode_to_text(b'\xff', 'utf-8')
        with patch('textoria_utf8_converter.from_bytes') as mocked:
            mocked.return_value.best.return_value = None
            with self.assertRaises(ValueError):
                detect_encoding(b'\xff')
