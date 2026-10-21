"""Musically grounded genre profiles and anti-repetition creative briefs.

Presets describe boundaries, not templates for cloning songs. Each request rotates
independent narrative, groove, arrangement, vocal and production choices.
"""
from __future__ import annotations

import json
import random
import secrets
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Genre:
    family: str
    identity: str
    bpm: tuple[int, int]
    grooves: tuple[str, ...]
    instruments: tuple[str, ...]
    vocals: tuple[str, ...]
    arrangements: tuple[str, ...]
    productions: tuple[str, ...]
    exclusions: str
    conventions: str


GENRES: dict[str, Genre] = {
    'Blues': Genre('blues', 'Expressive roots blues with call-and-response and space for an emotional turn', (60, 120),
        ('slow 12/8 sway', 'medium 4/4 shuffle', 'loping straight-eighth groove', 'syncopated acoustic pulse'),
        ('electric guitar, Hammond organ, walking bass', 'resonator guitar, foot percussion', 'harmonica, piano, live drums', 'clean guitar, upright bass, sparse drums'),
        ('weathered contralto, unhurried storytelling', 'expressive tenor with dynamic grit', 'intimate baritone, conversational phrasing', 'soulful alto with restrained vibrato'),
        ('sparse guitar opening, band joins after verse one', 'rhythm-first opening and answered vocal phrases', 'brief instrumental turnaround between stanzas', 'stop-time final chorus'),
        ('dry small-room capture', 'warm analog tape saturation', 'unpolished one-take live-room feel'),
        'trap drums, EDM drops, glossy synthpop, pitch-corrected pop vocals',
        'Respect blues phrasing, tension and release; 12-bar harmony is optional, not compulsory.'),
    'Swamp Blues': Genre('blues', 'Earthy, hypnotic swamp blues; jaw harp is essential, audible but never a gimmick', (58, 103),
        ('lazy 12/8 drag', 'muddy mid-tempo pocket', 'hypnotic straight 4/4', 'slow half-time stomp'),
        ('jaw harp, tremolo guitar, swampy bass and loose snare', 'jaw harp, resonator slide, dirty harmonica and brushed drums', 'jaw harp, low organ drones, muted guitar and rim clicks'),
        ('deep relaxed male baritone, tactile diction', 'gravelly contralto, spare moans', 'low smoky voice, behind-the-beat', 'raw alto with drawn-out vowel endings'),
        ('jaw-harp pickup before guitar answers', 'bass and jaw harp establish a pulse before the singer', 'slide-guitar solo after second hook', 'break to jaw harp and a single drum before final refrain'),
        ('humid tape-room ambience', 'dark vintage tube saturation', 'intimate back-porch recording with audible breath'),
        'EDM, trap hi-hats, glossy pop, pristine robotic vocals, stadium reverb',
        'Keep the jaw harp in the texture, leave air between lines; evoke place through concrete details, not stock bayou clichés.'),
    'Delta Blues': Genre('blues', 'Intimate Delta blues with fingerstyle or bottleneck expression', (54, 106),
        ('elastic free-time pulse', 'alternating-bass 4/4', 'lilting 6/8', 'unhurried 12-bar shuffle'),
        ('steel-string fingerpicked guitar and foot tap', 'resonator slide guitar and sparse heel rhythm', 'open-tuned bottleneck guitar with handclaps'),
        ('rough-edged alto with narrative precision', 'weathered tenor, intimate natural breath', 'spoken-sung baritone, expressive timing'),
        ('unaccompanied instrumental prelude', 'guitar lick answers every second vocal couplet', 'rubato break before last verse', 'single-note slide outro'),
        ('one-microphone dry wooden room', 'raw live take with string noise', 'narrow vintage mono recording'),
        'EDM, metal rhythm guitar, glossy synth pads, stadium drums, orchestral strings',
        'Use authentic narrative phrasing and acoustic dynamics; AAB can be used but need not dominate every song.'),
    'Chicago Blues': Genre('blues', 'Urban electric Chicago blues with conversational lead and sharp band interplay', (62, 124),
        ('slow 12/8 electric sway', 'swinging 4/4 shuffle', 'driving walking-bass shuffle', 'lazy minor blues pocket'),
        ('hollow-body electric guitar, harmonica and organ', 'stinging electric guitar, upright bass and tight kit', 'blues piano, electric guitar and brushed snare'),
        ('husky alto with understated bite', 'gritty tenor with call-and-response phrasing', 'warm baritone with punchy rhythmic attacks'),
        ('band riff answers each verse', 'harmonica takes an eight-bar break', 'guitar solo followed by stop-time chorus', 'piano turnaround ends without fade'),
        ('warm close-miked club ensemble', 'live studio tape with audible amplifier growl', 'small jazz-blues room with natural spill'),
        'trap, synthetic drums, EDM, pitch-corrected pop leads, arena-metal guitars',
        'Honor electric blues dynamics, tight ensemble playing, guitar/harp answers; avoid endlessly repeating 12-bar clichés.'),
    'Whiskey Blues': Genre('blues', 'Road-worn adult blues about consequences and resilience, not compulsory drinking references', (55, 100),
        ('slow bruised 12/8', 'restrained straight 4/4', 'rolling late-night shuffle', 'heavy slow two-step'),
        ('warm overdriven guitar, upright bass and Hammond', 'fingerpicked electric guitar, low piano and brushes', 'raspy harmonica, tremolo guitar and restrained kit'),
        ('rough velvet baritone with cracks on held notes', 'raspy contralto with dry delivery', 'low tenor, intimate spoken-sung verses'),
        ('bare vocal over one guitar for first verse', 'slow band swell after second refrain', 'short crying guitar solo as emotional turning point', 'last refrain sung nearly a cappella'),
        ('dim small-bar analog room', 'gritty close-mic live take', 'tape-worn late-night club atmosphere'),
        'party-pop, novelty drinking song, EDM, trap, autotune, choir, glossy vocal stacks',
        'Convey lived consequences, earned regret or endurance; do not require whiskey, bottle or bar in every lyric.'),
    'Smoky Blues': Genre('blues', 'Intimate smoky lounge blues with subtle harmonic color and restrained performance', (52, 94),
        ('slow 12/8 jazz-blues sway', 'relaxed brushed swing', 'sparse minor-key 6/8', 'laid-back late-night ballad pulse'),
        ('warm hollow-body guitar, brushed drums and upright bass', 'tenor sax, muted piano and bass', 'Hammond, soft electric guitar and intimate kit'),
        ('breathy smoky alto with deliberate silence', 'mellow worn baritone, quiet intensity', 'deep contralto with subtle phrasing', 'restrained tenor with soft falsetto turns'),
        ('instrumental sax prologue', 'piano intro with late vocal entrance', 'instrumental bridge with one muted horn', 'last line left hanging over soft guitar'),
        ('close dry vintage lounge', 'dim analog ribbon-mic texture', 'low-noise trio playing in one room'),
        'arena rock, bright pop synths, EDM, trap, aggressive guitar walls, robotic tuning',
        'Favor nuanced harmony and pauses; smoky means intimate and atmospheric, not automatically cigarettes or alcohol.'),
    'Metal': Genre('metal', 'Powerful guitar-driven metal with purposeful dynamic contrast', (86, 180),
        ('driving double-time 4/4', 'half-time riff stomp', 'syncopated riff pulse', 'galloping 6/8'),
        ('down-tuned guitar pair, articulate bass and live kit', 'harmonized lead guitar and crushing rhythm guitars', 'tight palm-muted guitars and tom-heavy drums'),
        ('aggressive clean lead with controlled grit', 'raw midrange belt and gang responses', 'alternating harsh and melodic vocals', 'low commanding lead with dynamic sustain'),
        ('cold opening riff with sudden full-band entry', 'melodic lift into anthemic refrain', 'instrumental harmony break', 'double-time bridge returning to a heavy ending'),
        ('punchy modern metal mix with defined bass', 'raw rehearsal-room weight', 'wide yet unpolished guitar stacks'),
        'EDM drop, trap hi-hats, glossy dance-pop, cartoon villain lyrics, overcompressed wall of noise',
        'Give each riff an identity, preserve rhythmic clarity, and vary song structure without forcing a predictable power chorus.'),
    'Swamp Metal': Genre('metal', 'Southern swamp metal, humid sludge weight and sinister organic groove', (60, 135),
        ('lurching sludge half-time', 'hypnotic Southern swing', 'slow polyrhythmic 4/4', 'swampy doom pulse'),
        ('drop-tuned fuzz guitars, thick bass and floor toms', 'slide-guitar textures under crushing riffs', 'dirty rhythm guitars, organ drone and distant harmonica', 'low fuzz guitar with sparse jaw harp pulse'),
        ('hoarse baritone roar with intelligible lines', 'ritualistic low growl and rough sung refrain', 'rasped contralto with menacing dynamics'),
        ('droning intro turning into huge downbeat', 'slide-guitar lead over half-time breakdown', 'silence before final unison riff', 'extended bass-and-toms bridge'),
        ('humid distorted rehearsal space', 'thick analog fuzz with raw drum transients', 'dark live amp room'),
        'slick hair-metal guitars, EDM, trap, pop polish, synthetic orchestral swells',
        'Use crushing organic groove and meaningful tension, not decorative swamp words or genre stereotypes.'),
    'Death Metal': Genre('metal', 'Technical and visceral death metal with coherent narrative and precise extreme rhythm', (115, 230),
        ('blast-beat burst over tremolo riffs', 'technical syncopated double kick', 'half-time crushing section', 'rapid shifting-meter assault'),
        ('tremolo-picked distorted guitars, fretless bass and rapid drums', 'low-tuned guitars, tight double-kick and dissonant leads', 'chromatic riffing with precise snare and bass attack'),
        ('deep articulate growl', 'midrange harsh bark with dynamic variation', 'alternating cavernous growls and piercing rasp'),
        ('dissonant instrumental overture', 'riff cycle with abrupt metric transition', 'instrumental solo over contrasting half-time', 'unresolved final breakdown'),
        ('tight aggressive mix with audible bass notes', 'organic brutal live kit', 'dry high-definition guitars with minimal reverb'),
        'pop chorus, hair-metal vocals, EDM, glossy synths, autotune, cheerful major-key hooks',
        'Use rhythmic precision and comprehensible thematic progression. Harsh vocals are a texture, not a license for filler or random gore.'),
    'Glam Metal': Genre('metal', 'Melodic theatrical glam metal with memorable hooks and stylish lead guitar', (96, 158),
        ('upbeat straight 4/4 rock drive', 'big half-time arena ballad', 'swaggering syncopated shuffle', 'energetic palm-muted eighth-note pulse'),
        ('bright layered guitars, melodic bass and splashy live drums', 'overdriven rhythm guitars, keyboard accents and soaring lead', 'harmonized guitar leads and fat snare'),
        ('expressive clean high-register tenor', 'dramatic powerful alto with controlled rasp', 'swaggering male tenor with harmonized hooks'),
        ('theatrical guitar pickup', 'pre-chorus tension opening into sung hook', 'melodic solo with harmonized finale', 'final chorus with altered ending'),
        ('glossy vintage-inspired arena mix without brickwall loudness', 'punchy 1980s analog studio', 'wide gated-snare rock room'),
        'death growls, extreme blast beats, doom sludge, EDM, trap, minimalist acoustic folk',
        'Balance melodic drama, riffs and bold image with specific storytelling rather than generic nightlife slogans.'),
    'Hair Metal': Genre('metal', 'Hook-forward 1980s hard rock/hair metal with guitar virtuosity and layered harmonies', (90, 162),
        ('anthemic straight 4/4', 'fast driving guitar shuffle', 'power-ballad 6/8', 'swinging mid-tempo groove'),
        ('hot-rodded lead guitar, thick rhythm stack and big drums', 'dual melodic guitars, driving bass and snare-heavy kit', 'crunchy guitar and soaring harmonized lead break'),
        ('raspy high tenor with gang-vocal answers', 'smoky midrange lead with soaring chorus', 'belted alto and layered melodic harmonies'),
        ('single-guitar intro into big riff', 'build from intimate verse to huge hook', 'eight-bar expressive guitar solo', 'final refrain with octave-up ad libs'),
        ('bright analog 1980s rock recording', 'live arena-room drum ambience', 'warm guitar-forward studio mix'),
        'blast beats, deep death growls, EDM, trap, downtempo sludge, orchestral pop',
        'Keep big hooks and lead guitars, but vary emotional stakes; not every song should celebrate partying or romance.'),
}

# Historical controls retain their behavior, while new genre names are canonical.
ALIASES = {'Chicago Electric': 'Chicago Blues', 'Delta': 'Delta Blues', 'Swamp': 'Swamp Blues',
           'Contemporary': 'Blues', 'Acoustic': 'Delta Blues', 'Soul Blues': 'Smoky Blues',
           'Memphis': 'Blues', 'Piedmont': 'Delta Blues', 'Texas': 'Blues', 'Jump Blues': 'Blues'}

THEMES = (
    'a missed opportunity that unexpectedly opens a new door',
    'a small act of defiance that changes a relationship',
    'making peace with a decision without romanticizing it',
    'a complicated homecoming and a surprising welcome',
    'a good intention with unintended consequences',
    'a promise kept when nobody is looking',
    'an ordinary object holding two contradictory memories',
    'an unresolved conversation across generations',
    'the cost of winning an argument',
    'a friendship tested by a quiet betrayal',
    'a job, craft or calling that changes the speaker',
    'a celebration that hides an unsaid goodbye',
    'trying to start over in a place that remembers everything',
    'a comic human mistake that becomes a turning point',
    'confronting a false story told about oneself',
    'the uneasy freedom of leaving something behind',
    'an old rivalry turning into reluctant respect',
    'loss of certainty followed by hard-earned resolve',
    'a reunion that reveals two different truths',
    'finding tenderness in an unglamorous moment',
)
POVS = ('first-person confessional', 'second-person direct address', 'third-person character portrait',
        'two alternating voices', 'present-tense scene', 'narrator looking back from years later')
IMAGES = ('a half-repaired household tool', 'the silence after a train has passed, without using a train as a motif',
          'a hand-written note with one missing line', 'a kitchen clock that runs fast', 'a busted guitar string',
          'a coffee-stained envelope', 'a neglected garden', 'a receipt that outlasts a relationship',
          'a church bell heard from far away without religious clichés', 'a cracked photograph frame',
          'a borrowed jacket', 'a doorway with new paint')


def canonical_genre(name: str) -> str:
    value = ALIASES.get(name, name)
    if value not in GENRES:
        raise ValueError(f'Unknown genre/style: {name}')
    return value


def is_metal(name: str) -> bool:
    return GENRES[canonical_genre(name)].family == 'metal'


def genre_names() -> tuple[str, ...]:
    return tuple(GENRES)


def make_variation(name: str, recent: tuple[dict, ...] | list[dict] = (), seed: int | None = None) -> dict:
    genre_name = canonical_genre(name)
    profile = GENRES[genre_name]
    rng = random.Random(secrets.randbits(64) if seed is None else seed)
    history = [r for r in recent if isinstance(r, dict)]
    seen = {(str(x.get('theme')), str(x.get('groove')), str(x.get('arrangement'))) for x in history}
    last_themes = {str(x.get('theme')) for x in history[:6]}
    last_grooves = {str(x.get('groove')) for x in history[:2]}
    winner = None
    best = -1
    for _ in range(100):
        sample = dict(
            genre=genre_name, family=profile.family, theme=rng.choice(THEMES), pov=rng.choice(POVS),
            detail=rng.choice(IMAGES), groove=rng.choice(profile.grooves), bpm=rng.randint(*profile.bpm),
            instruments=rng.choice(profile.instruments), vocal=rng.choice(profile.vocals),
            arrangement=rng.choice(profile.arrangements), production=rng.choice(profile.productions),
            identity=profile.identity, conventions=profile.conventions, exclusions=profile.exclusions,
        )
        signature = (sample['theme'], sample['groove'], sample['arrangement'])
        score = (100 if signature not in seen else 0) + (20 if sample['theme'] not in last_themes else 0) + (10 if sample['groove'] not in last_grooves else 0)
        if score > best:
            best = score
            winner = sample
        if score == 130:
            break
    return winner


def variation_prompt(v: dict) -> str:
    return (f"Genre: {v['genre']} ({v['family']}). Musical identity: {v['identity']}. "
            f"Genre conventions: {v['conventions']}\n"
            f"Chosen creative twist: {v['theme']}. Point of view: {v['pov']}. "
            f"Concrete detail (if it fits naturally): {v['detail']}.\n"
            f"Tempo: around {v['bpm']} BPM; groove: {v['groove']}; instrumental palette: {v['instruments']}; "
            f"vocal direction: {v['vocal']}; arrangement arc: {v['arrangement']}; "
            f"production character: {v['production']}.\n"
            f"Exclude unsuitable sounds: {v['exclusions']}.\n"
            "Treat these as independent creative choices, NOT mandatory words to sing. "
            "Never default to recycled hooks or copy existing songs. Preserve any explicit user brief above optional theme suggestions.")


def variation_json(v: dict) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)
