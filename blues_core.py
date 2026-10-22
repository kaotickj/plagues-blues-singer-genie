"""Pure-Python generation, persistence and Ollama transport."""
from __future__ import annotations

import json
from contextlib import contextmanager, closing
import os
import random
import re
import shutil
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

APP_NAME = "PlaguesMusicStudio"
LEGACY_APP_NAME = "PlaguesBluesSingerGenie"
from genre_presets import genre_names, variation_prompt, make_variation
STYLES = list(genre_names())
GENDERS = ["Any", "Masculine", "Feminine", "Neutral"]
FIRST = {
    "Masculine": ["Eddie", "Willie", "Calvin", "Leon", "Otis", "Rufus", "Sam", "Isaiah", "Morris", "Ray", "Jesse", "Arthur", "Ellis", "Franklin"],
    "Feminine": ["Ruby", "Loretta", "Nina", "Estelle", "Clara", "Mavis", "Pearl", "Rosie", "Willa", "Della", "Ida", "Vera", "Josie", "Lucille"],
    "Neutral": ["Billie", "Jules", "Frankie", "Robin", "Casey", "Jackie", "Lee", "Sam", "Lou", "Jess", "Sidney", "Charlie"],
}
LAST = ["Mercer", "Holloway", "Rivers", "Bell", "Caldwell", "Bishop", "Hayes", "Monroe", "Carter", "Hawkins", "Sutton", "Reed", "Price", "Turner", "Wells", "Crawford", "Bennett", "Stokes", "Dawson", "Vaughn"]
NICKNAMES = ["Afterhours", "Midnight", "Blue Note", "Lowdown", "Honeycomb", "Railroad", "Velvet", "Trouble", "Red Clay", "Copper", "Six-String", "Backstreet", "Slowburn", "Smokehouse"]


def paths():
    """Upgrade without overwriting previous data or deleting legacy directories."""
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".local" / "share"))
    root = base / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    legacy = base / LEGACY_APP_NAME
    settings_source = legacy / 'settings.json'
    settings_target = root / 'settings.json'
    if not settings_target.exists() and settings_source.is_file():
        shutil.copy2(settings_source, settings_target)
    db_source = legacy / 'library.sqlite3'
    db_target = root / 'library.sqlite3'
    if not db_target.exists() and db_source.is_file():
        # Backup includes committed WAL transactions. Previous DB remains unchanged.
        with closing(sqlite3.connect(str(db_source))) as old_db, closing(sqlite3.connect(str(db_target))) as new_db:
            with new_db:
                old_db.backup(new_db)
    return root


def make_names(count=10, gender="Any", seed=None, excluded=()):
    if not 1 <= count <= 100:
        raise ValueError("Count must be between 1 and 100")
    if gender not in GENDERS:
        raise ValueError("Invalid gender")
    rng = random.Random(seed)
    pool = FIRST[gender] if gender != "Any" else [n for group in FIRST.values() for n in group]
    names = []
    seen = {name.casefold() for name in excluded}
    for _ in range(count * 80):
        first, last = rng.choice(pool), rng.choice(LAST)
        style = rng.randrange(5)
        if style == 0:
            name = f'{first} "{rng.choice(NICKNAMES)}" {last}'
        elif style == 1:
            name = f'{rng.choice(NICKNAMES)} {first} {last}'
        elif style == 2:
            name = f'{first} {last}'
        elif style == 3:
            name = f'{first} "{rng.choice(NICKNAMES)}"'
        else:
            name = f'{first} {last} & the {rng.choice(["Backbeat", "Blue Hour", "Night Shift", "River Road"])} Band'
        if name.casefold() not in seen:
            seen.add(name.casefold())
            names.append(name)
            if len(names) == count:
                return names
    raise RuntimeError("Could not generate enough unique names")


def parse_names(response: str, count: int) -> list[str]:
    """Accept plain lists or JSON arrays without rendering model control text."""
    try:
        decoded = json.loads(response)
        if isinstance(decoded, dict):
            decoded = decoded.get("names", [])
        if isinstance(decoded, list):
            raw = [str(v.get("name", "")) if isinstance(v, dict) else str(v) for v in decoded]
        else:
            raw = response.splitlines()
    except (ValueError, TypeError):
        raw = response.splitlines()
    output, seen = [], set()
    for item in raw:
        item = re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", item.strip()).strip(' \t"')
        if not item or len(item) > 90 or item.casefold() in seen or item.startswith(("[", "{", "```")):
            continue
        if item.casefold() in {"names", "name"}:
            continue
        seen.add(item.casefold())
        output.append(item)
        if len(output) == count:
            break
    return output


def build_prompt(task: str, style: str, artist: Optional[dict], idea: str, count=10, gender="Any", variation: dict | None = None) -> str:
    context = f"Existing fictional artist: {json.dumps(artist, ensure_ascii=False)}" if artist else "Create new fictional work."
    twist = variation_prompt(variation or make_variation(style))
    universal = (
        "You are an expert music creative director and editor. Artist identities and histories are FICTIONAL; "
        "the genre references are musically grounded. Avoid imitating named artists, invented historical claims, "
        "caricatures, recycled hooks, filler, predictable props or scenery. Never default to a game or fantasy theme. "
        f"{context}\nUser direction (takes priority): {idea or 'Use a fresh concept.'}\n" + twist + "\n"
    )
    instructions = {
        "Stage names": f"Generate exactly {count} DISTINCT credible stage names suited to {style}. Presentation: {gender}. One name per line.",
        "Artist biography": "Write a distinct fictional artist biography: origins, sonic identity, vocal character, stage presence, career arc and concise web-ready bio. Keep claims fictional and internally consistent.",
        "Artist style guide": "Write a reusable style bible: musical conventions, BPM ranges, grooves, lyrical philosophy, vocal delivery, arrangements, live instruments, recording methods, production limits and signature choices. Avoid overly restrictive formulas.",
        "Album concept": "Propose a distinctive album title and cohesive 12-track sequence with a different song concept for each, narrative mood arc, arrangements, cover direction and one-paragraph website description. Rotate tempo, point-of-view and sonic density among tracks.",
        "Three album concepts": "Propose THREE contrasting albums in the selected musical family, each with a distinct title, emotional arc, palette and 12 original track titles. Prevent repeated motifs and identical song structures across the three.",
        "Song lyrics": "Write complete ORIGINAL lyrics with a purposeful hook and expressive delivery, rooted in the selected genre. Use the appropriate section forms, never a genre-neutral template.",
        "Suno style prompt": "Return a Suno-ready Style of Music description with concrete instruments, tempo, vocal techniques, performance dynamics, studio texture and contrasting Exclude Styles. Reflect the current genre, not a generic blues prompt.",
        "Website promo": "Write a truthful fictional artist/album promo for the selected genre, a descriptive SEO title, concise meta description, six phrases and social copy. Never invent real credentials or sales history.",
    }
    if task not in instructions:
        raise ValueError("Unknown creative task")
    return universal + instructions[task]


class Ollama:
    def __init__(self, url="http://127.0.0.1:11434", timeout=180):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.url + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                return json.load(resp)
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Cannot reach Ollama at {self.url}: {exc.reason}") from exc

    def models(self):
        data = self._request("/api/tags")
        return sorted([m["name"] for m in data.get("models", []) if m.get("name")])

    def generate(self, model: str, prompt: str):
        if not model.strip():
            raise ValueError("Choose a local Ollama model first")
        data = self._request("/api/generate", {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.85, "num_predict": 2600}})
        return data.get("response", "").strip()


class Library:
    def __init__(self, location=None):
        self.location = str(location or (paths() / "library.sqlite3"))
        with self._db() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS artists (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    style TEXT NOT NULL, bio TEXT NOT NULL DEFAULT '', created TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY, artist_id INTEGER REFERENCES artists(id),
                    task TEXT NOT NULL, content TEXT NOT NULL, created TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS creative_history (
                    id INTEGER PRIMARY KEY, artist_id INTEGER REFERENCES artists(id),
                    genre TEXT NOT NULL, variation_json TEXT NOT NULL, created TEXT NOT NULL
                );
            """)

    @contextmanager
    def _db(self):
        conn = sqlite3.connect(self.location)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            with conn:
                yield conn
        finally:
            conn.close()

    def artists(self):
        with self._db() as c:
            return [dict(r) for r in c.execute("SELECT * FROM artists ORDER BY name")]

    def add_artist(self, name, style):
        name = name.strip()
        if not name:
            raise ValueError("Artist name is empty")
        with self._db() as c:
            c.execute("INSERT OR IGNORE INTO artists(name,style,created) VALUES (?,?,?)", (name, style, datetime.now(timezone.utc).isoformat()))
            return c.execute("SELECT id FROM artists WHERE name=? COLLATE NOCASE", (name,)).fetchone()[0]

    def set_bio(self, artist_id, bio):
        with self._db() as c:
            c.execute("UPDATE artists SET bio=? WHERE id=?", (bio, artist_id))

    def drafts(self):
        with self._db() as c:
            return [dict(r) for r in c.execute("SELECT * FROM drafts ORDER BY id DESC")]

    def add_draft(self, artist_id, task, content):
        with self._db() as c:
            c.execute("INSERT INTO drafts(artist_id,task,content,created) VALUES (?,?,?,?)", (artist_id, task, content, datetime.now(timezone.utc).isoformat()))

    def recent_variations(self, genre: str, artist_id=None, limit=12):
        # Reuse only the relevant artist's history; standalone requests have their own history.
        with self._db() as c:
            rows = c.execute("SELECT variation_json FROM creative_history WHERE genre=? AND artist_id IS ? ORDER BY id DESC LIMIT ?", (genre, artist_id, limit))
            return [json.loads(row[0]) for row in rows]

    def recent_song_samples(self, artist_id=None, limit=8):
        """Read saved track titles and refrain excerpts without loading whole songs into prompts.

        This is a lightweight memory aid, not a music-plagiarism detector.
        """
        if not 1 <= limit <= 20:
            raise ValueError('Song history limit must be between 1 and 20')
        with self._db() as c:
            rows = c.execute("SELECT content FROM drafts WHERE task='Song lyrics' AND artist_id IS ? ORDER BY id DESC LIMIT ?",
                             (artist_id, limit))
            texts = [r[0] for r in rows]
        samples = []
        for raw in texts:
            title, lyrics = '', ''
            match = re.search(r'(?m)^TITLE\s*\n([^\r\n]+)', raw)
            if match:
                title = match.group(1).strip()
                lyrics_match = re.search(r'(?ms)^LYRICS\s*\n(.*?)(?=^STYLE OF MUSIC\s*$|\Z)', raw)
                lyrics = lyrics_match.group(1) if lyrics_match else ''
            else:
                try:
                    record = json.loads(raw)
                except (ValueError, TypeError):
                    record = {}
                if isinstance(record, dict):
                    title, lyrics = str(record.get('title', '')), str(record.get('lyrics', ''))
            if not title:
                continue
            hook = re.search(r'(?ms)^\[(?:Chorus|Refrain|Hook)(?:[^]\n]*)\]\s*\n(.*?)(?=^\[|\Z)', lyrics)
            lines = [line.strip() for line in (hook.group(1) if hook else '').splitlines() if line.strip() and not line.lstrip().startswith('[')]
            samples.append({'title': title[:120], 'hook': ' '.join(lines[:2])[:220]})
        return samples

    def record_variation(self, genre: str, artist_id, variation: dict):
        with self._db() as c:
            c.execute("INSERT INTO creative_history(artist_id,genre,variation_json,created) VALUES (?,?,?,?)",
                      (artist_id, genre, json.dumps(variation, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))


def load_settings():
    try:
        data = json.loads((paths() / "settings.json").read_text(encoding="utf-8"))
        return {"url": str(data.get("url", "http://127.0.0.1:11434")), "model": str(data.get("model", "")),
                "roles": data.get("roles", {}) if isinstance(data.get("roles", {}), dict) else {},
                "threshold": data.get("threshold", 85), "max_rewrites": data.get("max_rewrites", 2)}
    except (FileNotFoundError, ValueError, OSError):
        return {"url": "http://127.0.0.1:11434", "model": "", "roles": {}, "threshold": 85, "max_rewrites": 2}


def save_settings(data):
    target = paths() / "settings.json"
    values = {"url": data["url"], "model": data["model"], "roles": data.get("roles", {}),
              "threshold": data.get("threshold", 85), "max_rewrites": data.get("max_rewrites", 2)}
    target.write_text(json.dumps(values, indent=2), encoding="utf-8")
