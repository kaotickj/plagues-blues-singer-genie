import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import io

from blues_core import Library, Ollama, build_prompt, make_names, parse_names


class CoreTests(unittest.TestCase):
    def test_unique_names(self):
        names = make_names(50, gender="Neutral", seed=42)
        self.assertEqual(len(set(names)), 50)
        self.assertEqual(names, make_names(50, gender="Neutral", seed=42))

    def test_exclusions(self):
        first = make_names(10, seed=2)
        second = make_names(10, seed=2, excluded=first)
        self.assertFalse(set(first) & set(second))

    def test_name_parser(self):
        self.assertEqual(parse_names('1. Ruby Reed\n2. Eddie Rivers\n2. Eddie Rivers', 3), ['Ruby Reed', 'Eddie Rivers'])
        self.assertEqual(parse_names('{"names":["Mavis Bell", "Willa Hayes"]}', 2), ['Mavis Bell', 'Willa Hayes'])

    def test_prompt_real_world(self):
        prompt = build_prompt('Three album concepts', 'Delta', {'name':'Pearl Bell', 'bio':'Guitarist'}, 'heartbreak')
        self.assertIn('THREE', prompt)
        self.assertIn('Pearl Bell', prompt)
        self.assertIn('FICTIONAL', prompt)

    def test_sqlite_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            lib = Library(Path(temp) / 'test.db')
            artist_id = lib.add_artist('Pearl Bell', 'Memphis')
            self.assertEqual(artist_id, lib.add_artist('pearl bell', 'Delta'))
            lib.set_bio(artist_id, 'A fictional singer')
            lib.add_draft(artist_id, 'Album concept', 'One Last Morning')
            self.assertEqual(lib.artists()[0]['bio'], 'A fictional singer')
            self.assertEqual(lib.drafts()[0]['content'], 'One Last Morning')

    @patch('urllib.request.urlopen')
    def test_ollama_response(self, urlopen):
        urlopen.return_value.__enter__.return_value = io.BytesIO(b'{"models":[{"name":"qwen3:4b"}]}')
        self.assertEqual(Ollama().models(), ['qwen3:4b'])
        urlopen.return_value.__enter__.return_value = io.BytesIO(b'{"response":"Album lyrics"}')
        self.assertEqual(Ollama().generate('qwen3:4b', 'write'), 'Album lyrics')


if __name__ == '__main__':
    unittest.main()
