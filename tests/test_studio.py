"""Regression tests for model management, curated writing and blues production."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from curation import run_curation
from model_manager import _safe_member, validate_model_name, known_model_stores, verify_model
from music_engine import MusicConfig, make_ace_request, safe_song_filename, FORMATS
from name_engine import NameBank, validate_template
from suno import parse_suno, export_suno, song_prompt

SONG = {"title": "Some Things Never Leave",
        "lyrics": "[Intro - dry electric guitar]\n" +
                  "[Verse 1 - tender delivery]\n" + ("That old porch light keeps shining, even when nobody's home.\n" * 4) +
                  "[Chorus]\nI can carry this road, I can carry this road\n" * 2 +
                  "[Verse 2]\n" + ("The cold coffee on the counter reminds me what I have known.\n" * 4) +
                  "[Instrumental Break - twelve-bar guitar solo]\n[Chorus]\nI can carry this road, I can carry this road\n[Outro]\nThe porch light fades away",
        "style": "Slow Mississippi Delta blues, acoustic bottleneck slide, 68 BPM, soulful alto",
        "exclude_styles": "EDM, trap, orchestral pop"}


class NameBankTests(unittest.TestCase):
    def test_seed_persistence_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "library.sqlite3"
            db = NameBank(file)
            self.assertGreater(len(db.parts()), 100)
            first = db.generate(35, gender="Neutral", style="Swamp", seed=14)
            self.assertEqual(len(set(first)), 35)
            self.assertEqual(first, db.generate(35, gender="Neutral", style="Swamp", seed=14))
            db.add("nickname", "Tin Roof Sunday", style="Swamp", weight=7)
            db.add_pattern('{first} "{nickname}" {last}', 3) if False else None
            db.close()
            reopened = NameBank(file)
            self.assertTrue(any(x["value"] == "Tin Roof Sunday" for x in reopened.parts("nickname")))
            reopened.close()

    def test_validation_guards_against_template_injection(self):
        with self.assertRaises(ValueError):
            validate_template('{first.__class__}')
        with self.assertRaises(ValueError):
            validate_template('{prefix}')
        bank = NameBank()
        with self.assertRaises(ValueError):
            bank.add('nickname', 'Evil {malicious}')
        bank.close()

    def test_remove_and_exclusions(self):
        bank = NameBank()
        a = bank.generate(12, seed=3)
        b = bank.generate(12, seed=3, excluded=a)
        self.assertFalse(set(a) & set(b))
        entry = bank.parts('nickname')[0]
        bank.remove(entry['id'])
        self.assertFalse(any(x['id'] == entry['id'] for x in bank.parts('nickname')))
        bank.close()


class SunoTests(unittest.TestCase):
    def test_tagged_fields_separate(self):
        pkg = parse_suno(json.dumps(SONG), 'Delta')
        self.assertIn('[Instrumental Break', pkg.lyrics)
        self.assertIn('bottleneck', pkg.style)
        self.assertEqual(pkg.exclude_styles, 'EDM, trap, orchestral pop')
        self.assertIn('EXCLUDE STYLES', export_suno(pkg))
        self.assertIn('four STRING fields', song_prompt('Delta', None, 'heartbreak'))

    def test_audio_request_separates_sung_lyrics(self):
        pkg = parse_suno(json.dumps(SONG), 'Delta')
        req = make_ace_request(pkg, MusicConfig(output_format='flac'))
        self.assertEqual(req['lyrics'], pkg.lyrics)
        self.assertEqual(req['caption'], pkg.style)
        self.assertEqual(req['lm_negative_prompt'], pkg.exclude_styles)
        self.assertEqual(set(FORMATS), {'mp3','flac','wav','ogg','m4a'})
        self.assertEqual(safe_song_filename('Oh: the Blues?/'), 'Oh the Blues')


class CurationTests(unittest.TestCase):
    def test_successfully_cured_song(self):
        sequence = ["A nuanced Delta blues brief with groove and instrumentation details",
                    json.dumps(SONG), json.dumps(SONG),
                    json.dumps({'score':92,'approved':True,'feedback':'Great phrasing'})]
        seen = []
        def generate(model, prompt):
            seen.append(model)
            return sequence.pop(0)
        roles={role: role+'-model' for role in ('research','draft','edit','audit')}
        result=run_curation('Song lyrics','Delta',None,'',"http://127.0.0.1:11434",roles,generate=generate)
        self.assertTrue(result.approved)
        self.assertEqual(result.score,92)
        self.assertEqual(seen,['research-model','draft-model','edit-model','audit-model'])
        self.assertIsNotNone(result.suno)

    def test_rewrite_bounded_and_fails_closed(self):
        seen=[]
        def generate(model,prompt):
            seen.append(model)
            return json.dumps({'score':20,'approved':False,'feedback':'Poor authenticity'}) if model=='audit' else 'bad'
        roles={x:x for x in ('research','draft','edit','audit')}
        result=run_curation('Song lyrics','Delta',None,'',"http://127.0.0.1:11434",roles,
                            max_rewrites=1,generate=generate)
        self.assertFalse(result.approved)
        self.assertEqual(seen.count('audit'),2)
        self.assertEqual(seen.count('edit'),2)


class InstallSafetyTests(unittest.TestCase):
    def test_archives_validate_relative_paths(self):
        for value in ('../../etc/passwd', '/etc/passwd', 'C:\\Windows\\system32'):
            with self.assertRaises(ValueError): _safe_member(value)
        self.assertEqual(str(_safe_member('bin/ollama')), 'bin/ollama')

    def test_model_names(self):
        self.assertEqual(validate_model_name('qwen3:4b'), 'qwen3:4b')
        with self.assertRaises(ValueError): validate_model_name('qwen;rm -rf /')
        with self.assertRaises(ValueError): validate_model_name('--help')

    @patch('model_manager.Ollama')
    def test_model_show(self,mock_ollama):
        mock_ollama.return_value._request.return_value={
            'modelfile':'FROM sha256...', 'details':{'family':'qwen3','parameter_size':'4B'},
            'capabilities':['completion']}
        info=verify_model('http://localhost:11434','qwen3:4b')
        self.assertTrue(info['verified'])
        self.assertEqual(info['family'],'qwen3')


if __name__=='__main__': unittest.main()
