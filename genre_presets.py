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


# Every genre gets its own songwriting architecture. The profiles above control
# arrangement and sound; these rotate narrative craft and harmonic vocabulary.
# They are editorial prompts, not fixed song templates or words to be sung.
SONGCRAFT: dict[str, dict[str, tuple[str, ...]]] = {
    'Blues': {
        'forms': ('three evolving AAB stanzas without a repeated chorus', 'eight-bar narrative with a two-line refrain', 'slow verse/response with an instrumental answer', 'minor-key blues ballad with a late hook'),
        'hooks': ('a conversational question answered differently each time', 'a two-word phrase gaining meaning in successive stanzas', 'a refrain that changes its final word', 'an understated ironic reversal'),
        'harmonies': ('I-IV-V with a turnaround', 'minor I-IV-V color', 'eight-bar I-V-IV movement', 'soul-blues dominant ninth colors'),
    },
    'Swamp Blues': {
        'forms': ('hypnotic one-riff verse with sparse answered refrain', 'narrative verses separated by jaw-harp responses', 'half-time stomp with a contrasting bridge', 'six-eight drone with gradual lyrical revelation'),
        'hooks': ('a short low-register warning', 'a call-and-response against the jaw harp', 'a whispered phrase returning with changed context', 'a stubborn one-line mantra that evolves'),
        'harmonies': ('one-chord modal drone', 'I-IV swamp vamp', 'minor pentatonic two-chord movement', 'slow I-V turnback'),
    },
    'Delta Blues': {
        'forms': ('unaccompanied rubato AAB storytelling', 'alternating bass couplets with guitar replies', 'eight-bar acoustic narrative with no chorus', 'strophic travelogue with changing endings'),
        'hooks': ('a guitar answer instead of a sung chorus', 'a repeated opening line with altered payoff', 'a dry spoken-sung observation', 'a question left unanswered until the outro'),
        'harmonies': ('open-tuning I-IV-V', 'alternating tonic and dominant bass', 'modal slide-guitar drone', 'loose eight-bar blues turnaround'),
    },
    'Chicago Blues': {
        'forms': ('electric 12-bar with stop-time verse', 'walking-bass shuffle with shouted responses', 'slow minor electric blues with instrumental bridge', 'eight-bar nightclub narrative with piano turnaround'),
        'hooks': ('a band-unison answer to the singer', 'a punchy refrain with a changed final line', 'a wry two-line comeback', 'a harmonica motif carrying the hook'),
        'harmonies': ('dominant seventh I-IV-V', 'minor Chicago blues changes', 'I-VI-II-V turnaround', 'eight-bar jazz-blues changes'),
    },
    'Whiskey Blues': {
        'forms': ('first-person confession revealing the cost at the end', 'quiet aftermath told in three scenes', 'two-voice argument without a winner', 'slow redemption narrative with almost a cappella ending'),
        'hooks': ('a plain admission with a double meaning', 'a refrain whose meaning reverses at the end', 'an image of repair instead of self-pity', 'a short unfinished sentence completed later'),
        'harmonies': ('slow minor twelve-bar', 'soulful I-IV dominant vamp', 'descending minor bass movement', 'restrained eight-bar blues'),
    },
    'Smoky Blues': {
        'forms': ('minimalist lounge ballad with long instrumental spaces', 'late-night three-scene monologue', 'small jazz-blues stanza and sax interlude', 'quiet duet with unequal verses'),
        'hooks': ('a near-whispered closing phrase', 'a held note answered by sax', 'a lyrical pause that changes the meaning', 'a restrained refrain rather than a big chorus'),
        'harmonies': ('minor ninth jazz-blues color', 'slow ii-V turnback', 'muted dominant seventh vamp', 'chromatic bass movement over blues form'),
    },
    'Metal': {
        'forms': ('riff-led verse into asymmetric refrain', 'dual-guitar narrative with tempo-changing middle', 'through-composed sections returning to opening motif', 'galloping verse with contrasting half-time bridge'),
        'hooks': ('a rhythmic chant displaced against the riff', 'a melodic phrase with altered final repetition', 'an instrumental guitar motif as the hook', 'a call-and-response between lead and band'),
        'harmonies': ('minor pentatonic riff center', 'Phrygian riff with dissonant passing tones', 'natural-minor harmonized guitar movement', 'pedal-tone chromatic riff'),
    },
    'Swamp Metal': {
        'forms': ('slow sludge ritual with a brief faster rupture', 'Southern-groove narrative building to heavy silence', 'doom-laden riff cycle with extended bass bridge', 'two-section heavy swing with instrumental refrain'),
        'hooks': ('an ominous one-line chant that grows heavier', 'a slide-guitar figure replacing a chorus', 'a barked warning with different responses', 'a bass-and-drum motif emerging after each verse'),
        'harmonies': ('low minor riff drone', 'tritone sludge movement', 'blues-inflected down-tuned riff', 'Phrygian doom pedal tone'),
    },
    'Death Metal': {
        'forms': ('through-composed technical narrative without pop chorus', 'blastbeat passages interrupted by crushing half-time', 'dissonant instrumental chapters with harsh refrain', 'rapid shifting-meter riff cycle with decisive ending'),
        'hooks': ('a recurring rhythmic growled declaration', 'a short dissonant riff as the recurring motif', 'a harsh response phrase that changes each return', 'a wordless rhythmic punctuation'),
        'harmonies': ('chromatic diminished riffing', 'Phrygian dissonance and tritone leaps', 'minor-second pedal movement', 'atonal riff with resolved final root'),
    },
    'Glam Metal': {
        'forms': ('theatrical verse/pre-chorus with unexpected final chorus', 'glam rocker with spoken opening and guitar feature', 'dramatic power ballad resolving to a full-band chorus', 'upbeat riff anthem with lyrical contradiction'),
        'hooks': ('a soaring melodic title line with a lyrical twist', 'a harmonized call-and-response', 'a swaggering riff answered by vocal', 'a climactic pre-chorus question'),
        'harmonies': ('major-key guitar hooks with borrowed minor', 'I-bVII-IV rock movement', 'minor verse to major chorus', 'suspended-chord power-ballad lift'),
    },
    'Hair Metal': {
        'forms': ('arena riff with a late key change avoided unless earned', 'six-eight power ballad with restrained first half', 'fast dual-guitar rocker with gang-vocal refrain', 'mid-tempo hard-rock story with extended guitar solo'),
        'hooks': ('stacked vocal harmonies responding to lead', 'an octave-leaping singalong line', 'a melodic lead-guitar hook before the chorus', 'a refrain that shifts pronouns on the final return'),
        'harmonies': ('I-bVII-IV stadium-rock lift', 'minor-verse major-chorus contrast', 'six-eight suspended-chord ballad', 'pentatonic hard-rock turnaround'),
    },
}

EMOTIONAL_ARCS = (
    'certainty -> doubt -> a decisive but imperfect choice',
    'resentment -> uncomfortable recognition -> empathy',
    'false victory -> consequence -> quiet reckoning',
    'hope -> reversal -> a new kind of hope',
    'ordinary comedy -> painful truth -> earned humor',
    'isolation -> unexpected connection -> unresolved ambiguity',
    'memory -> confrontation -> changed understanding',
    'pressure -> refusal -> cost of that refusal',
)

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
    craft = SONGCRAFT[genre_name]
    rng = random.Random(secrets.randbits(64) if seed is None else seed)
    history = [r for r in recent if isinstance(r, dict) and r.get('genre', genre_name) == genre_name]
    # Prefer unused narrative material first, before optimizing musical variety.
    fresh_themes = [t for t in THEMES if t not in {h.get('theme') for h in history[:8]}] or list(THEMES)
    fields = ('theme', 'pov', 'groove', 'instruments', 'vocal', 'arrangement', 'production',
              'song_form', 'hook_device', 'harmony', 'emotional_arc')
    weights = dict(theme=80, pov=8, groove=24, instruments=14, vocal=10,
                   arrangement=18, production=8, song_form=30, hook_device=26,
                   harmony=13, emotional_arc=22)
    winner, best = None, -1
    for _ in range(150):
        sample = dict(
            genre=genre_name, family=profile.family, theme=rng.choice(fresh_themes), pov=rng.choice(POVS),
            detail=rng.choice(IMAGES), groove=rng.choice(profile.grooves), bpm=rng.randint(*profile.bpm),
            instruments=rng.choice(profile.instruments), vocal=rng.choice(profile.vocals),
            arrangement=rng.choice(profile.arrangements), production=rng.choice(profile.productions),
            song_form=rng.choice(craft['forms']), hook_device=rng.choice(craft['hooks']),
            harmony=rng.choice(craft['harmonies']), emotional_arc=rng.choice(EMOTIONAL_ARCS),
            identity=profile.identity, conventions=profile.conventions, exclusions=profile.exclusions,
        )
        # Earlier songs have more influence; avoid reusing a complete sonic and lyrical formula.
        score = 0
        for field in fields:
            repeated = next((i for i, h in enumerate(history[:12]) if h.get(field) == sample[field]), None)
            score += weights[field] if repeated is None else min(repeated, 8) * weights[field] // 12
        bpm_bucket = sample['bpm'] // 12
        if bpm_bucket not in {int(h.get('bpm', -100)) // 12 for h in history[:3]}:
            score += 16
        if score > best:
            winner, best = sample, score
    return winner


def variation_prompt(v: dict) -> str:
    return (f"Genre: {v['genre']} ({v['family']}). Musical identity: {v['identity']}. "
            f"Genre conventions: {v['conventions']}\n"
            f"Distinct SONG FORM: {v.get('song_form', 'genre-appropriate and variable')}; "
            f"HOOK MECHANIC: {v.get('hook_device', 'invent a credible new hook')}; "
            f"HARMONIC PALETTE: {v.get('harmony', 'musically grounded changes')}.\n"
            f"Specific narrative premise: {v['theme']}. Narrative voice: {v['pov']}. "
            f"Emotional arc: {v.get('emotional_arc', 'make a meaningful emotional turn')}. "
            f"Concrete detail (only if natural): {v['detail']}.\n"
            f"Tempo: around {v['bpm']} BPM; groove: {v['groove']}; instruments: {v['instruments']}; "
            f"vocal delivery: {v['vocal']}; arrangement: {v['arrangement']}; "
            f"production character: {v['production']}.\n"
            f"EXCLUDE incompatible sounds: {v['exclusions']}.\n"
            "These are compositional constraints, NOT words to sing or mandatory story props. "
            "Do not default to midnight, whiskey, crossroads, trains, demons, darkness or fire as generic imagery. "
            "Create a distinctive opening line, hook cadence and ending for this particular track. "
            "Never mimic a known performer or a previous track. The user's own brief takes priority over optional motifs.")


def variation_json(v: dict) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)
