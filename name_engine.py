"""Database-backed, user-extensible blues stage-name permutations.

Only the name bank and templates affect name generation. AI is never required.
"""
from __future__ import annotations

import random
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

KINDS = ('first', 'last', 'nickname', 'prefix', 'suffix', 'band')
TEMPLATES = (
    ('{first} {last}', 12),
    ('{first} "{nickname}" {last}', 12),
    ('{nickname} {first} {last}', 6),
    ('{prefix} {first} {last}', 5),
    ('{first} {last} {suffix}', 3),
    ('{first} {last} & The {band}', 6),
    ('{prefix} {first} "{nickname}" {last}', 2),
    ('{first} "{nickname}" {last} & The {band}', 2),
)
PARTS = {
    'first': {
        'masculine': 'Eddie Willie Calvin Leon Otis Rufus Isaiah Morris Ray Jesse Arthur Ellis Franklin Silas Amos Luther Booker Clarence Walter Earl Sonny',
        'feminine': 'Ruby Loretta Nina Estelle Clara Mavis Pearl Rosie Willa Della Ida Vera Josie Lucille Ada Etta Millie Sadie Mae Cora',
        'neutral': 'Billie Jules Frankie Robin Casey Jackie Lee Sam Lou Jess Sidney Charlie Stevie Harper Riley Jamie Morgan',
    },
    'last': 'Mercer Holloway Rivers Bell Caldwell Bishop Hayes Monroe Carter Hawkins Sutton Reed Price Turner Wells Crawford Bennett Stokes Dawson Vaughn Talley Raines Ramsey Devereaux Whitfield Cross Hinton Blackwell',
    'nickname': 'Afterhours|Blue Note|Lowdown|Honeycomb|Railroad|Velvet|Trouble|Red Clay|Copper|Six-String|Backstreet|Slowburn|Smokehouse|Long Road|Bluebird|High Water|Southside|Mississippi Moon|Ashes|Easy Money|Tin Roof|Sunday Morning|Honeydrip|Sundown|Old Soul',
    'prefix': 'Big|Little|Old|Young|Sweet|Rev.|Doc|Miss|Mr.|Lady|Professor|Brother|Sister|Captain|Papa|Mama',
    'suffix': 'Jr.|Sr.|III',
    'band': 'Backbeat Boys|Blue Hour Band|Night Shift|River Road Band|Heartbreakers|Blue Notes|Midnight Ramblers|Lowdown Kings|Velvet Aces|Memphis Shuffle|Southern Sound|Sunday Drivers',
}
# Component-style weights: global components remain eligible; style-specific entries
# are emphasized only when their style is selected.
from genre_presets import genre_names, ALIASES
STYLES = ('Any', *genre_names(), *ALIASES.keys())
GENDERS = ('Any', 'Masculine', 'Feminine', 'Neutral')
FIELDS = set(KINDS)
PLACEHOLDER = re.compile(r'\{([a-z]+)\}')


def validate_template(pattern):
    names = PLACEHOLDER.findall(pattern)
    if not names or len(pattern) > 150 or not set(names).issubset(FIELDS):
        raise ValueError('Template must use known placeholders such as {first} or {nickname}')
    if '{first}' not in pattern and '{nickname}' not in pattern:
        raise ValueError('Template needs {first} or {nickname}')
    if pattern.count('{') != len(names) or pattern.count('}') != len(names):
        raise ValueError('Malformed name template')
    return names


class NameBank:
    """Name components live in SQLite, alongside the artist library."""
    def __init__(self, db_path=':memory:'):
        self.db_path = str(db_path)
        if self.db_path == ':memory:':
            self.conn = sqlite3.connect(':memory:')
        else:
            self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS name_parts (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                value TEXT NOT NULL,
                gender TEXT NOT NULL DEFAULT 'Any',
                style TEXT NOT NULL DEFAULT 'Any',
                weight INTEGER NOT NULL DEFAULT 1 CHECK(weight BETWEEN 1 AND 20),
                UNIQUE(kind, value, gender, style)
            );
            CREATE TABLE IF NOT EXISTS name_patterns (
                id INTEGER PRIMARY KEY,
                pattern TEXT NOT NULL UNIQUE,
                weight INTEGER NOT NULL DEFAULT 1 CHECK(weight BETWEEN 1 AND 20)
            );
        ''')
        count = self.conn.execute('SELECT COUNT(*) FROM name_parts').fetchone()[0]
        if count == 0:
            self.seed()
        self._seed_metal_parts()

    def seed(self):
        with self.conn:
            for kind, data in PARTS.items():
                if isinstance(data, dict):
                    for gender, values in data.items():
                        for value in values.split():
                            self.conn.execute('INSERT OR IGNORE INTO name_parts (kind,value,gender) VALUES (?,?,?)', (kind, value, gender.title()))
                else:
                    values = data.split('|') if '|' in data else data.split()
                    for value in values:
                        self.conn.execute('INSERT OR IGNORE INTO name_parts (kind,value) VALUES (?,?)', (kind, value))
            self.conn.executemany('INSERT OR IGNORE INTO name_patterns(pattern,weight) VALUES (?,?)', TEMPLATES)

    def _seed_metal_parts(self):
        """Idempotent additions for metal names, including existing user databases."""
        parts = {
            'nickname': 'Iron Veil|Nightglass|Ash Crown|Vesper|Black Thorn|Tempest|Razor Sky|Silent Reign|Steel Oath|Wraith',
            'prefix': 'Iron|Dark|Saint|Lady|Lord|Raven',
            'band': 'Iron Choir|Wicked Saints|Riven Crown|Fire Circuit|Last Signal|Winter Reign|Glass Serpents|Ashborne',
        }
        with self.conn:
            for kind, choices in parts.items():
                for value in choices.split('|'):
                    self.conn.execute('INSERT OR IGNORE INTO name_parts(kind,value,style,weight) VALUES (?,?,?,?)',
                                      (kind, value, 'Metal', 5))

    def parts(self, kind=None):
        if kind and kind not in KINDS:
            raise ValueError('Unknown component type')
        if kind:
            return [dict(x) for x in self.conn.execute('SELECT * FROM name_parts WHERE kind=? ORDER BY value', (kind,))]
        return [dict(x) for x in self.conn.execute('SELECT * FROM name_parts ORDER BY kind,value')]

    def patterns(self):
        return [dict(x) for x in self.conn.execute('SELECT * FROM name_patterns ORDER BY id')]

    def add(self, kind, value, gender='Any', style='Any', weight=1):
        value = value.strip()
        if kind not in KINDS or gender not in GENDERS or style not in STYLES:
            raise ValueError('Invalid component settings')
        if not value or len(value) > 80 or any(c in value for c in '{}\r\n'):
            raise ValueError('Component must be 1-80 characters on one line')
        if not 1 <= weight <= 20:
            raise ValueError('Weight out of range')
        with self.conn:
            self.conn.execute('INSERT INTO name_parts(kind,value,gender,style,weight) VALUES (?,?,?,?,?)', (kind, value, gender, style, weight))

    def remove(self, component_id):
        with self.conn:
            self.conn.execute('DELETE FROM name_parts WHERE id=?', (component_id,))

    def add_pattern(self, pattern, weight=1):
        validate_template(pattern)
        if not 1 <= weight <= 20:
            raise ValueError('Weight out of range')
        with self.conn:
            self.conn.execute('INSERT INTO name_patterns(pattern,weight) VALUES (?,?)', (pattern, weight))

    def remove_pattern(self, pattern_id):
        with self.conn:
            self.conn.execute('DELETE FROM name_patterns WHERE id=?', (pattern_id,))

    def generate(self, count=10, gender='Any', style='Any', seed=None, excluded=()):
        if not 1 <= count <= 100 or gender not in GENDERS or style not in STYLES:
            raise ValueError('Invalid generation settings')
        rng = random.Random(seed)
        pools = defaultdict(list)
        for item in self.parts():
            if gender != 'Any' and item['kind'] == 'first' and item['gender'] not in ('Any', 'Neutral', gender):
                continue
            if style != 'Any' and item['style'] not in ('Any', style):
                from genre_presets import is_metal
                if not (item['style'] == 'Metal' and is_metal(style)):
                    continue
            weighting = item['weight'] * (3 if style != 'Any' and item['style'] == style else 1)
            pools[item['kind']].extend([item['value']] * weighting)
        patterns = self.patterns()
        patterns = [p for p in patterns if all(pools.get(field) for field in validate_template(p['pattern']))]
        if not patterns:
            raise ValueError('No valid name templates have populated components')
        names, seen = [], {s.casefold() for s in excluded}
        for _ in range(count * 250):
            p = rng.choices(patterns, weights=[p['weight'] for p in patterns])[0]
            fields = set(validate_template(p['pattern']))
            tokens = {key: rng.choice(pools[key]) for key in fields}
            name = p['pattern'].format_map(tokens)
            if name.casefold() in seen:
                continue
            seen.add(name.casefold())
            names.append(name)
            if len(names) == count:
                return names
        raise RuntimeError('Not enough unique names available; add more components or patterns')

    def close(self):
        self.conn.close()
