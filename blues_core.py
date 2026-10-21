"""Pure-Python generation, persistence and Ollama transport."""
from __future__ import annotations

import json
from contextlib import contextmanager
import os
import random
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

APP_NAME = "PlaguesBluesSingerGenie"
STYLES = ["Chicago Electric", "Delta", "Texas", "Memphis", "Piedmont", "Swamp", "Jump Blues", "Soul Blues", "Acoustic", "Contemporary"]
GENDERS = ["Any", "Masculine", "Feminine", "Neutral"]
FIRST = {
    "Masculine": ["Eddie", "Willie", "Calvin", "Leon", "Otis", "Rufus", "Sam", "Isaiah", "Morris", "Ray", "Jesse", "Arthur", "Ellis", "Franklin"],
    "Feminine": ["Ruby", "Loretta", "Nina", "Estelle", "Clara", "Mavis", "Pearl", "Rosie", "Willa", "Della", "Ida", "Vera", "Josie", "Lucille"],
    "Neutral": ["Billie", "Jules", "Frankie", "Robin", "Casey", "Jackie", "Lee", "Sam", "Lou", "Jess", "Sidney", "Charlie"],
}
LAST = ["Mercer", "Holloway", "Rivers", "Bell", "Caldwell", "Bishop", "Hayes", "Monroe", "Carter", "Hawkins", "Sutton", "Reed", "Price", "Turner", "Wells", "Crawford", "Bennett", "Stokes", "Dawson", "Vaughn"]
NICKNAMES = ["Afterhours", "Midnight", "Blue Note", "Lowdown", "Honeycomb", "Railroad", "Velvet", "Trouble", "Red Clay", "Copper", "Six-String", "Backstreet", "Slowburn", "Smokehouse"]


def paths():
    root = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".local" / "share")) / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
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


def build_prompt(task: str, style: str, artist: Optional[dict], idea: str, count=10, gender="Any") -> str:
    context = f"Existing fictional artist: {json.dumps(artist, ensure_ascii=False)}" if artist else "Create new fictional work."
    universal = (
        "You are a skilled blues music creative director. All artists and personal histories are FICTIONAL, "
        "but the music is rooted in real-world blues traditions, not games or fantasy. "
        "Avoid borrowing a real living artist's identity, fabricating real achievements, or relying on caricatures. "
        "Be specific, memorable, emotionally credible, and avoid overusing crossroads, whiskey, midnight, and trains. "
        "Do not mention Fallout, Goodneighbor, or a post-apocalyptic setting. "
        f"Primary style: {style}. {context}\nUser direction: {idea or 'Use original ideas.'}\n"
    )
    instructions = {
        "Stage names": f"Generate exactly {count} DISTINCT, believable stage names. Presentation: {gender}. Output one name per line, no commentary.",
        "Artist biography": "Write a fictional artist biography with hometown, era, influences (without imitation), defining voice, instrumentation, career story, and short one-paragraph web bio. Label fictional details as fictional in the internal profile, not as historical claims.",
        "Artist style guide": "Create a reusable artist style bible: subgenre, vocal timbre, accent guidance without stereotypes, instrumentation, grooves, BPM ranges, lyrical themes, arrangement constraints, production approach, and a reusable Suno-ready style prompt.",
        "Album concept": "Propose one compelling album title and a cohesive 12-track listing with a one-sentence song concept for each; include sequencing, theme, mood arc, cover-art direction, and a concise website description.",
        "Three album concepts": "Propose THREE distinct real-world blues albums for a broad audience. Give each an original title, one-paragraph concept, distinct sonic palette and exactly 12 track titles. Make the releases complementary, not repetitive.",
        "Song lyrics": "Write complete ORIGINAL blues lyrics with labeled sections, a singable hook, believable conversational imagery, and no imitation of a specific copyrighted song. Match this artist's established sound if provided.",
        "Suno style prompt": "Return a production-ready Suno style prompt specifying instruments, groove, tempo, vocal quality, recording environment, arrangement, and negative constraints. Then a second, shorter alternate version.",
        "Website promo": "Write a truthful, compelling website artist/album description, SEO page title, meta description, 6 search phrases, and a social caption. Do not assert fabricated real-world credentials.",
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


def load_settings():
    try:
        data = json.loads((paths() / "settings.json").read_text(encoding="utf-8"))
        return {"url": str(data.get("url", "http://127.0.0.1:11434")), "model": str(data.get("model", ""))}
    except (FileNotFoundError, ValueError, OSError):
        return {"url": "http://127.0.0.1:11434", "model": ""}


def save_settings(data):
    target = paths() / "settings.json"
    target.write_text(json.dumps({"url": data["url"], "model": data["model"]}, indent=2), encoding="utf-8")
