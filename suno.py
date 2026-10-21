"""Suno Custom Mode formatting and predictable independent output fields.

Tag vocabulary is guidance, not a stable or strictly interpreted Suno API.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from genre_presets import GENRES, canonical_genre, make_variation, variation_prompt

PRESETS = {
    "Chicago Electric": {
        "style": "Traditional Chicago electric blues, 70 BPM slow 12/8 shuffle, close-miked gravelly lead voice, overdriven hollow-body electric guitar, tasteful harmonica answers, upright bass, brushed snare, warm Hammond organ, lived-in live-room ambience, analog tape warmth",
        "exclude": "synth-pop, EDM, trap drums, auto-tune, glossy pop vocals, arena-rock guitars, orchestral strings, crowd noise",
        "cue": "[Intro - solo electric guitar, two bars; smoky room ambience]",
    },
    "Delta": {
        "style": "Intimate Delta blues, 67 BPM loose 4/4, fingerpicked resonator slide guitar, heel-tap percussion, weathered expressive lead vocal, open tuning, raw one-room mono recording, elastic timing",
        "exclude": "electronic drums, EDM, bright pop synths, stadium reverb, glossy production, choral backing vocals",
        "cue": "[Intro - unaccompanied resonator guitar slide; loose tempo]",
    },
    "Swamp": {
        "style": "Slow swamp blues, 72 BPM laid-back 12/8, swampy jaw harp pulse, tremolo electric guitar, dirty harmonica, fat bass, rim-click snare, low growling soulful voice, humid Southern back-room sound, tape saturation",
        "exclude": "polished pop, electronic kick, trap hi-hats, high-speed metal, orchestral strings, choir, pitch-corrected vocals",
        "cue": "[Intro - hypnotic jaw harp and tremolo guitar, eight bars]",
    },
    "Texas": {
        "style": "Texas blues shuffle, 100 BPM swinging 4/4, confident gritty blues vocal, punchy electric guitar, walking bass, crisp live drums, piano fills, gritty tube-amp tone, small-room sound",
        "exclude": "EDM, synthesizer leads, quantized drum loops, autotune, epic film score, stadium reverb",
        "cue": "[Intro - stinging electric guitar lead over a swinging shuffle]",
    },
    "Memphis": {
        "style": "Memphis blues and Southern soul, 76 BPM, husky expressive vocal, warm electric guitar, piano, organ, tight bass and drums, restrained horn stabs, vintage analog studio, gospel-inflected phrasing",
        "exclude": "glossy EDM, modern trap, huge orchestral swells, autotune, arena reverb",
        "cue": "[Intro - soulful organ and understated guitar call-and-response]",
    },
    "Piedmont": {
        "style": "Piedmont acoustic blues, 92 BPM syncopated ragtime fingerpicking, warm conversational singing, acoustic six-string guitar, intimate natural room, crisp alternating bass, understated foot tapping",
        "exclude": "heavy distortion, electronic beats, synth pads, orchestra, overproduced pop, arena drums",
        "cue": "[Intro - alternating bass fingerpicked guitar, playful syncopation]",
    },
    "Jump Blues": {
        "style": "1940s-style jump blues energy, 132 BPM swung 4/4, exuberant lead singing, honking tenor sax, piano triplets, walking upright bass, crisp snare and ride cymbal, punchy small-band recording",
        "exclude": "EDM, trap drums, modern pop synths, heavy metal guitars, slow ambient pads",
        "cue": "[Intro - punchy tenor sax riff and walking upright bass]",
    },
    "Soul Blues": {
        "style": "Deep Southern soul blues, 66 BPM slow 12/8, expressive smoky alto lead voice, Hammond organ, clean electric guitar, warm bass, gentle drums, raw dynamics, close vintage vocals",
        "exclude": "EDM, trap, bright bubblegum pop, robotic vocals, auto-tune, huge choir, distorted metal guitars",
        "cue": "[Intro - soft Hammond organ with muted electric guitar responses]",
    },
    "Acoustic": {
        "style": "Bare-bones acoustic blues, 74 BPM, open-tuned fingerpicked steel-string guitar, honest intimate vocal, subtle bottleneck slides, soft foot percussion, rustic dry-room recording",
        "exclude": "electronic instruments, drum machines, orchestral strings, pop synths, overproduced effects",
        "cue": "[Intro - solo acoustic guitar, free-time rubato pickup]",
    },
    "Contemporary": {
        "style": "Contemporary roots blues, 86 BPM soulful groove, natural expressive lead vocals, electric blues guitar, Hammond, warm bass, organic drums, modern clarity with analog warmth, no excessive compression",
        "exclude": "EDM drop, trap drums, autotune, arena metal, synthetic pads, glossy pop chorus",
        "cue": "[Intro - intimate blues guitar motif over live rhythm section]",
    },
}

TAGS = ("[Intro]", "[Verse 1]", "[Chorus]", "[Verse 2]", "[Instrumental Break]", "[Bridge]", "[Outro]")
TAG_PATTERN = re.compile(r"\[(?:intro|verse(?:\s+\d+)?|chorus|pre-chorus|bridge|outro|instrumental(?:\s+break)?|solo|hook|refrain|interlude|spoken\s+word|breakdown)(?:\s*[-:][^\]\r\n]+)?\]", re.I)


@dataclass(frozen=True)
class SunoPackage:
    title: str
    lyrics: str
    style: str
    exclude_styles: str


def song_prompt(style: str, artist: dict | None, idea: str, variation: dict | None = None) -> str:
    """Dedicated genre direction while respecting separate Suno Custom Mode fields."""
    info = json.dumps(artist or {}, ensure_ascii=False)
    plan = variation or make_variation(style)
    genre = GENRES[canonical_genre(style)]
    if genre.family == 'metal':
        structure = ("Use a structure fitting this METAL subgenre, e.g. [Intro - guitar riff], [Verse 1], "
                     "[Pre-Chorus] / [Refrain] / [Chorus] where musically appropriate, "
                     "[Breakdown - half-time riff], [Guitar Solo], [Outro]. Vary the order and section lengths. "
                     "Death metal may use a recurring refrain instead of a pop-style chorus. "
                     "Harsh vocal, fry and growl cues are permissible, but keep words intelligible.")
    else:
        structure = ("Use a BLUES-appropriate form: short [Intro], several [Verse] sections, "
                     "[Chorus] or [Refrain] when the hook suits it, [Instrumental Break] for call-and-response, "
                     "and a purposeful [Outro]. Choose AAB, 12-bar, 8-bar, verse/refrain, or a narrative variation as fitting, "
                     "not the same repeated 12-bar form for every track.")
    return f"""Write a COMPLETELY ORIGINAL song for Suno Custom Mode. Genre: {canonical_genre(style)}.
Musical direction and varied creative constraints:
{variation_prompt(plan)}
Established artist (fictional): {info}
User's creative brief (override optional motifs): {idea or 'Develop a believable, specific story.'}
Return ONLY one valid JSON object with four STRING fields, all nonempty: "title", "lyrics", "style", "exclude_styles". No code fences.
LYRICS must contain sung words and concise square-bracketed section/instrument/vocal directions, such as [Intro - muted guitar], [Verse 1 - sung low], [Instrumental Break - bass solo], [Outro - cut to silence]. Unbracketed text WILL be sung, so never put non-song instructions in it.
STRUCTURE: {structure}
STYLE OF MUSIC field must be a concrete, distinctive genre-correct production brief: instruments, rough BPM {plan['bpm']}, groove, timbre, vocal performance, arrangement and recording texture. Avoid reusing the same phrasing across songs.
EXCLUDE_STYLES field must be comma-separated and describe unwanted audible features appropriate to the selected genre, not a list of lyrics topics: {genre.exclusions}.
NO performer-name imitation, filler, stock choruses, obligatory whisky/train/crossroads tropes, unrelated subgenres, or game lore. Favor an emotional progression and fresh images over overblown adjective lists."""


def _drop_fences(value: str) -> str:
    value = value.strip()
    value = re.sub(r'^```(?:json|text)?\s*', '', value, flags=re.I)
    return re.sub(r'\s*```$', '', value).strip()


def parse_suno(raw: str, tradition: str = "Chicago Electric") -> SunoPackage:
    """Strict fields with a graceful fallback to raw tagged lyrics."""
    default = PRESETS.get(tradition, PRESETS['Contemporary'])
    if tradition not in PRESETS:
        profile = GENRES[canonical_genre(tradition)]
        direction = make_variation(tradition)
        default = {'style': variation_prompt(direction), 'exclude': profile.exclusions}
    body = _drop_fences(raw)
    try:
        decoded = json.loads(body)
    except (ValueError, TypeError):
        # Try a JSON object embedded among model framing text.
        start, end = body.find('{'), body.rfind('}')
        try:
            decoded = json.loads(body[start:end + 1]) if start >= 0 and end > start else {}
        except (ValueError, TypeError):
            decoded = {}
    if not isinstance(decoded, dict):
        decoded = {}
    title = str(decoded.get('title') or 'Untitled Blues').strip()[:140]
    lyrics = str(decoded.get('lyrics') or body).strip()
    style = str(decoded.get('style') or default['style']).strip()
    excludes = decoded.get('exclude_styles') or decoded.get('exclude') or default['exclude']
    if isinstance(excludes, list):
        excludes = ', '.join(map(str, excludes))
    excludes = str(excludes).strip()
    if not lyrics:
        raise ValueError('The model returned no lyrics')
    if not TAG_PATTERN.search(lyrics):
        lyrics = '[Verse 1]\n' + lyrics
    return SunoPackage(title=title, lyrics=lyrics, style=style, exclude_styles=excludes)


def export_suno(package: SunoPackage) -> str:
    return f'TITLE\n{package.title}\n\nLYRICS\n{package.lyrics}\n\nSTYLE OF MUSIC\n{package.style}\n\nEXCLUDE STYLES (ADVANCED OPTIONS)\n{package.exclude_styles}\n'
