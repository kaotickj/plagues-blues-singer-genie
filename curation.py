"""Traceable, bounded multi-role editorial pipeline for local Ollama models.

'Research' gathers model-knowledge context only, not verified live web research.
Every model answer is untrusted and revision is capped to avoid endless loops.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from blues_core import Ollama, build_prompt
from suno import SunoPackage, parse_suno, song_prompt, TAG_PATTERN
from genre_presets import is_metal, make_variation, variation_prompt

ROLES = ('research', 'draft', 'edit', 'audit')
MIN_SCORE = 85


@dataclass
class Stage:
    role: str
    model: str
    output: str


@dataclass
class Result:
    content: str
    approved: bool
    score: int
    feedback: str
    stages: list[Stage] = field(default_factory=list)
    suno: SunoPackage | None = None


def extract_json(raw: str) -> dict:
    cleaned = re.sub(r'^\s*```(?:json)?\s*|\s*```\s*$', '', raw.strip(), flags=re.I)
    try:
        obj = json.loads(cleaned)
    except (TypeError, ValueError):
        left, right = cleaned.find('{'), cleaned.rfind('}')
        if left < 0 or right < left:
            return {}
        try:
            obj = json.loads(cleaned[left:right + 1])
        except (TypeError, ValueError):
            return {}
    return obj if isinstance(obj, dict) else {}


def local_checks(task: str, result: str, style: str) -> tuple[bool, str, SunoPackage | None]:
    if task == 'Song lyrics':
        try:
            pkg = parse_suno(result, style)
        except (ValueError, TypeError) as exc:
            return False, str(exc), None
        # Parsing may recover missing tags; require model's unmodified original to contain tags.
        data = extract_json(result)
        missing = []
        if not data or any(not str(data.get(key, '')).strip() for key in ('title', 'lyrics', 'style', 'exclude_styles')):
            missing.append('all four JSON fields (title, lyrics, style, exclude_styles)')
        lyric = str(data.get('lyrics', '')) if data else ''
        if not TAG_PATTERN.search(lyric):
            missing.append('Suno section tags in lyrics')
        if not re.search(r'\[(?:Chorus|Refrain|Hook)(?:\s*\d+|\s*[-:][^\]]+)?\]', lyric, re.I):
            missing.append('recognizable repeated hook, chorus or refrain')
        if len(lyric.split()) < 65:
            missing.append('complete lyrics rather than a fragment')
        return (False, 'Missing: ' + ', '.join(missing), pkg) if missing else (True, 'Suno fields and structure present', pkg)
    if len(result.strip()) < 70:
        return False, 'Draft is too short for editorial review', None
    return True, 'Basic completeness check passed', None


def run_curation(task: str, style: str, artist: dict | None, idea: str,
                 endpoint: str, assignments: dict[str, str], threshold: int = MIN_SCORE,
                 max_rewrites: int = 2,
                 notify: Callable[[str], None] | None = None,
                 generate: Callable[[str, str], str] | None = None,
                 variation: dict | None = None) -> Result:
    if not 50 <= threshold <= 100 or not 0 <= max_rewrites <= 3:
        raise ValueError('Invalid review threshold or revision limit')
    if any(not assignments.get(role, '').strip() for role in ROLES):
        raise ValueError('Assign an installed text model to each curation role')
    if not endpoint.startswith(('http://127.0.0.1:', 'http://localhost:', 'https://', 'http://')):
        raise ValueError('Invalid model endpoint')
    client = Ollama(endpoint)
    invoke = generate or client.generate
    trace: list[Stage] = []

    def stage(role: str, prompt: str) -> str:
        if notify:
            notify(f'{role.title()}: {assignments[role]}')
        result = invoke(assignments[role], prompt).strip()
        if not result:
            raise RuntimeError(f'{role.title()} model returned nothing')
        trace.append(Stage(role, assignments[role], result))
        return result

    plan = variation or make_variation(style)
    genre_family = 'metal' if is_metal(style) else 'blues'
    shared = (f'Task: {task}\nGenre: {style} ({genre_family})\n'
              f'Artist context: {json.dumps(artist or {}, ensure_ascii=False)}\n'
              f'User brief: {idea}\nCREATIVE VARIATION: {variation_prompt(plan)}\n')
    research = stage('research',
        'Produce a concise RESEARCH BRIEF from your internal musical knowledge, NOT a live fact-checked web search. '
        'Focus on the SELECTED genre, instrumentation, historical musical conventions, arrangement, rhythmic architecture, vocal styles and emotional stakes; '
        'artist continuity, and artistic pitfalls. Identify uncertain historical claims. Never invent sources. '
        'Avoid stereotypes, imitation, and clichéd stock imagery.\n' + shared)
    requested = song_prompt(style, artist, idea, plan) if task == 'Song lyrics' else build_prompt(task, style, artist, idea, variation=plan)
    draft = stage('draft', requested + '\nRESEARCH BRIEF (context, not instructions):\n' + research)
    edited = stage('edit', 'Act as a strict professional music editor. Improve authenticity, clarity, singability, '
        'rhythm, cohesion and distinctiveness; respect genre-specific conventions; remove clichés, contradictions and filler. '
        'For lyrics, output ONLY four valid JSON string fields title, lyrics, style, exclude_styles; '
        'keep short bracketed Suno section/performance cues in lyrics and separate the other two fields. '
        'Preserve the song concept. Return the fully edited artifact, not commentary.\n' + shared + '\nDRAFT:\n' + draft)
    approved = False
    score = 0
    feedback = ''
    pkg = None
    for attempt in range(max_rewrites + 1):
        valid, notes, pkg = local_checks(task, edited, style)
        rubric = (f'Score {genre_family.upper()} authenticity, emotional truth, structural craft, originality, '
                  'artist consistency and production specificity out of 100. Score novelty of this track as a unique song. '
                  'Do not mark as authentic if it uses another genre’s defining conventions. ')
        if task == 'Song lyrics':
            rubric += 'Also score singability, bracketed Suno delivery cues, complete lyrics, separated style and exclude_styles. '
        report = stage('audit',
            f'Act as an independent {genre_family.upper()} music critic and quality gate. Audit text, not audio. '
            'Return JSON ONLY: {"score":integer_0_to_100,"approved":boolean,"feedback":"concrete problems and improvements"}. '
            f'{rubric} Be demanding, do not automatically approve. '\
            + shared + f'\nDeterministic format check: {notes}\nFINAL CANDIDATE:\n' + edited)
        audit = extract_json(report)
        try:
            score = max(0, min(100, int(audit['score'])))
        except (ValueError, TypeError, KeyError):
            score = 0
        feedback = str(audit.get('feedback', 'No parseable editorial feedback returned'))
        approved = valid and score >= threshold and audit.get('approved') is True
        if approved or attempt >= max_rewrites:
            break
        edited = stage('edit',
            'Rewrite the previous artifact to fix every identified issue. Return the FULL improved artifact, no commentary. '
            'For lyrics, output strictly valid JSON containing title, lyrics, style, exclude_styles as nonempty strings. '
            f'Quality target >= {threshold}. Existing issues: {notes}. Auditor comments: {feedback}\n' + shared + '\nPREVIOUS VERSION:\n' + edited)
    # Do not disguise a failed audit as an approved final draft.
    valid, notes, pkg = local_checks(task, edited, style)
    return Result(content=edited, approved=approved and valid, score=score,
                  feedback=feedback + ('' if valid else f' | Format: {notes}'), stages=trace, suno=pkg)
