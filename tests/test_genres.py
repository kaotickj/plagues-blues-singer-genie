"""Genre boundaries, anti-repeat sampling, multi-genre audits and preserved data."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from blues_core import Library, build_prompt, paths, APP_NAME
from curation import run_curation
from genre_presets import GENRES, canonical_genre, genre_names, make_variation, variation_prompt
from music_engine import MusicConfig, make_ace_request
from name_engine import NameBank
from suno import parse_suno, song_prompt


class GenreTests(unittest.TestCase):
    def test_exact_new_styles_and_legacy_aliases(self):
        self.assertEqual(tuple(GENRES), (
            'Blues', 'Swamp Blues', 'Delta Blues', 'Chicago Blues', 'Whiskey Blues',
            'Smoky Blues', 'Metal', 'Swamp Metal', 'Death Metal', 'Glam Metal', 'Hair Metal'))
        self.assertEqual(canonical_genre('Chicago Electric'), 'Chicago Blues')
        self.assertEqual(canonical_genre('Delta'), 'Delta Blues')
        with self.assertRaises(ValueError):
            make_variation('EDM')

    def test_every_genre_produces_valid_distinct_direction(self):
        for name in genre_names():
            plan = make_variation(name, seed=29)
            self.assertEqual(plan['genre'], name)
            self.assertGreaterEqual(plan['bpm'], GENRES[name].bpm[0])
            self.assertLessEqual(plan['bpm'], GENRES[name].bpm[1])
            self.assertIn(plan['groove'], GENRES[name].grooves)
            self.assertIn(plan['vocal'], GENRES[name].vocals)
            self.assertIn('genre', variation_prompt(plan).lower())
        self.assertTrue(all('jaw harp' in x.lower() for x in GENRES['Swamp Blues'].instruments))

    def test_rotation_avoids_recent_themes_and_grooves(self):
        previous = []
        for seed in range(6):
            plan = make_variation('Death Metal', previous, seed=seed)
            self.assertNotIn(plan['theme'], {x['theme'] for x in previous[:6]})
            self.assertNotIn((plan['theme'], plan['groove'], plan['arrangement']),
                             {(x['theme'],x['groove'],x['arrangement']) for x in previous})
            previous.insert(0,plan)
        self.assertEqual(make_variation('Blues', seed=7), make_variation('Blues', seed=7))

    def test_metal_lyrics_and_audit_not_blues_only(self):
        song = {'title':'A Town That Forgot Its Name',
                'lyrics':'[Intro - down-tuned riff]\n[Verse 1]\n' + ('The signs wore off the streets where we were born.\n' * 10)
                + '[Refrain]\nCall out the names we lost!\n[Breakdown - slow half-time riffs]\n'
                + '[Verse 2]\n' + ('Our neighbors wrote the truth on doors at dawn.\n' * 7)
                + '[Refrain]\nCall out the names we lost!\n[Outro]\nRemember us.',
                'style':'Death metal, articulate growls, tremolo-picked guitars, blast beat, 188 BPM',
                'exclude_styles':'pop hooks, autotune, EDM'}
        heard = []
        seq = ['Precise rhythm, brutal contrast, lyrical arc',json.dumps(song),json.dumps(song),
               json.dumps({'score':94,'approved':True,'feedback':'Distinct metal song'})]
        def ai(model, prompt):
            heard.append((model,prompt))
            return seq.pop(0)
        roles={x:x for x in ('research','draft','edit','audit')}
        result=run_curation('Song lyrics','Death Metal',None,'', 'http://127.0.0.1:11434', roles, generate=ai,
                            variation=make_variation('Death Metal',seed=11))
        self.assertTrue(result.approved)
        self.assertIn('METAL', heard[-1][1])
        self.assertNotIn('BLUES EDITOR',heard[-1][1])
        self.assertIn('Death Metal', heard[1][1])
        self.assertIn('EXCLUDE_STYLES', heard[1][1])
        pkg = parse_suno(json.dumps(song),'Death Metal')
        self.assertEqual(pkg.exclude_styles, 'pop hooks, autotune, EDM')
        self.assertIn('Death metal', pkg.style)
        request=make_ace_request(pkg,MusicConfig(bpm=188,scale='minor'))
        self.assertEqual(request['keyscale'],'E minor')
        self.assertEqual(request['lyrics'],pkg.lyrics)

    def test_genre_correct_prompts_and_name_generator(self):
        for style in ('Whiskey Blues','Smoky Blues','Swamp Metal','Glam Metal','Hair Metal'):
            self.assertIn(style, song_prompt(style,None,'a grounded story'))
            self.assertIn(style, build_prompt('Three album concepts',style,None,'a grounded story'))
        bank=NameBank()
        names=bank.generate(20,style='Death Metal',seed=104)
        self.assertEqual(len(names), len(set(names)))
        self.assertGreater(len(bank.parts()),100)
        bank.close()

    def test_history_is_artist_specific_and_persistent(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Library(Path(directory)/'lib.db')
            artist=db.add_artist('Selena Rains','Metal')
            data=make_variation('Swamp Metal',seed=2)
            db.record_variation('Swamp Metal', artist, data)
            self.assertEqual(db.recent_variations('Swamp Metal', artist),[data])
            self.assertEqual(db.recent_variations('Swamp Metal', None),[])
            self.assertEqual(db.recent_variations('Swamp Blues', artist),[])
            self.assertEqual(Library(Path(directory)/'lib.db').recent_variations('Swamp Metal',artist),[data])

    def test_legacy_data_migrates_without_destroying_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            old=base/'PlaguesBluesSingerGenie'
            old.mkdir()
            old_db=Library(old/'library.sqlite3')
            old_db.add_artist('Mavis Holloway','Delta')
            (old/'settings.json').write_text('{"url":"http://127.0.0.1:11535","model":"qwen3:4b"}')
            with patch.dict(os.environ, {'LOCALAPPDATA':tmp}):
                newpath=paths()
                self.assertEqual(newpath.name,APP_NAME)
                self.assertEqual(Library().artists()[0]['name'],'Mavis Holloway')
                self.assertEqual(json.loads((newpath/'settings.json').read_text())['model'],'qwen3:4b')
                self.assertTrue((old/'library.sqlite3').is_file())

if __name__ == '__main__':
    unittest.main()

class AlbumOriginalityTests(unittest.TestCase):
    """Sound palette and actual saved-song novelty are separate checks."""

    def test_every_genre_has_distinct_songwriting_choices(self):
        from genre_presets import SONGCRAFT
        self.assertEqual(set(SONGCRAFT), set(GENRES))
        for genre in GENRES:
            profile = SONGCRAFT[genre]
            for key in ('forms', 'hooks', 'harmonies'):
                self.assertGreaterEqual(len(profile[key]), 4)
            plan = make_variation(genre, seed=33)
            self.assertIn(plan['song_form'], profile['forms'])
            self.assertIn(plan['hook_device'], profile['hooks'])
            self.assertIn(plan['harmony'], profile['harmonies'])
            self.assertIn(plan['song_form'], variation_prompt(plan))

    def test_album_rotation_avoids_previous_structures(self):
        recent = []
        for seed in range(6):
            plan = make_variation('Chicago Blues', recent, seed=seed)
            self.assertNotIn(plan['theme'], {x['theme'] for x in recent})
            if recent:
                self.assertNotEqual(plan['song_form'], recent[0]['song_form'])
            recent.insert(0, plan)

    def test_previous_saved_song_refrain_and_title_are_detected(self):
        from suno import export_suno, SunoPackage
        from curation import local_checks
        with tempfile.TemporaryDirectory() as directory:
            lib = Library(Path(directory) / 'library.db')
            artist = lib.add_artist('Lucille Wilder', 'Smoky Blues')
            raw = SunoPackage('A Door Without a Key',
                              '[Verse 1]\n' + 'A simple line with a different story today.\n' * 12
                              + '[Chorus]\nI kept the door unlocked for all those years\n'
                              + 'Then lost the only key I knew\n[Outro]\nGoodbye',
                              'Smoky Blues with sax', 'EDM')
            lib.add_draft(artist, 'Song lyrics', export_suno(raw))
            prior = lib.recent_song_samples(artist)
            self.assertEqual(prior[0]['title'], raw.title)
            self.assertIn('unlocked', prior[0]['hook'])
            self.assertEqual(lib.recent_song_samples(None), [])
            valid, msg, _ = local_checks('Song lyrics', json.dumps(raw.__dict__), 'Smoky Blues', prior)
            self.assertFalse(valid)
            self.assertIn('duplicates', msg)

    def test_new_song_prompt_uses_specific_form_hook_and_harmony(self):
        plan = make_variation('Death Metal', seed=101)
        prompt = song_prompt('Death Metal', None, 'personal consequences', plan)
        self.assertIn(plan['song_form'], prompt)
        self.assertIn(plan['hook_device'], prompt)
        self.assertIn(plan['harmony'], prompt)
        self.assertNotIn('Blues editor', prompt)
