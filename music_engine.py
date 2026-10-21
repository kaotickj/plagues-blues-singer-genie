"""ACE-Step 1.5 synthesis via documented ace-server API or existing GGML CLI.

Based on Goodneighbor Blues' proven ace-lm -> ace-synth Vulkan strategy.
No arbitrary shell execution, no bundling of third-party model weights.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from suno import SunoPackage

FORMATS = {"mp3": ["-c:a", "libmp3lame", "-b:a", "256k"],
           "flac": ["-c:a", "flac"],
           "wav": ["-c:a", "pcm_s24le"],
           "ogg": ["-c:a", "libvorbis", "-q:a", "6"],
           "m4a": ["-c:a", "aac", "-b:a", "256k"]}
DEFAULT_NEGATIVE = "synthpop, EDM, trap beats, glossy autotune, orchestral film music"
_AUD_LOCK = threading.Lock()  # In-process mutex. Server worker also serializes via its queue.


@dataclass(frozen=True)
class MusicConfig:
    mode: str = "server"  # 'server' or 'cli'
    server_url: str = "http://127.0.0.1:8080"
    lm_executable: str = ""
    synth_executable: str = ""
    model_dir: str = ""
    device: str = "Vulkan0"
    seconds: int = 210
    bpm: int = 72
    key: str = "E"
    scale: str = "major"
    music_model: str = "acestep-v15-turbo-Q8_0.gguf"
    filename: str = ""
    output_format: str = "mp3"
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"


def safe_song_filename(title: str) -> str:
    value = re.sub(r"[^A-Za-z0-9 _.-]", "", title).strip(" ._")[:90]
    return value or "untitled-song"


def check_tool(path: str) -> str:
    if not path:
        raise FileNotFoundError("A required audio tool path is missing")
    found = shutil.which(path) or (str(Path(path).expanduser()) if Path(path).expanduser().is_file() else "")
    if not found:
        raise FileNotFoundError(f"Required program not found: {path}")
    return str(found)


def verify_ace(config: MusicConfig) -> dict:
    """Probe an actual service or check installed CLI/model files. No automatic downloads."""
    if config.mode == 'server':
        if not config.server_url.startswith(('http://127.0.0.1:', 'http://localhost:', 'https://')):
            raise ValueError("Use an SSH tunnel to reach a remote ACE-Step server securely")
        req = urllib.request.Request(config.server_url.rstrip('/') + '/props')
        with urllib.request.urlopen(req, timeout=15) as response:
            props = json.load(response)
        return {'mode':'server', 'status':props.get('status', {}), 'url':config.server_url}
    if config.mode != 'cli':
        raise ValueError('Unknown music backend')
    found = {'mode':'cli', 'lm':check_tool(config.lm_executable),
             'synth':check_tool(config.synth_executable), 'models':str(Path(config.model_dir).expanduser())}
    directory = Path(config.model_dir).expanduser()
    if not directory.is_dir():
        raise FileNotFoundError(f'ACE model directory not found: {directory}')
    names = ('acestep-5Hz-lm-0.6B-Q8_0.gguf','Qwen3-Embedding-0.6B-Q8_0.gguf',config.music_model,'vae-BF16.gguf')
    # Existing Goodneighbor Blues ace.cpp build resolves model selection inside --models.
    found['model_files'] = [p.name for p in directory.glob('*.gguf')]
    if not found['model_files']:
        raise FileNotFoundError(f'No GGUF models found under {directory}')
    found['expected'] = list(names)
    return found


def make_ace_request(song: SunoPackage, config: MusicConfig) -> dict:
    if not song.lyrics.strip() or not song.style.strip():
        raise ValueError('Approve a complete lyrics and style package before generating audio')
    if not (30 <= config.seconds <= 600 and 45 <= config.bpm <= 260):
        raise ValueError('Duration must be 30–600 seconds and BPM 45–260')
    if config.scale not in ('major', 'minor'):
        raise ValueError('Unknown musical scale')
    sft = 'sft' in config.music_model.lower()
    return {
        'caption': song.style[:2500], 'lyrics': song.lyrics[:20000],
        'duration': config.seconds, 'bpm':config.bpm, 'keyscale':config.key + ' ' + config.scale,
        'vocal_language':'en', 'timesignature':'4/4', 'batch_size':1,
        'inference_steps': 50 if sft else 8, 'shift':1.0 if sft else 3.0,
        'guidance_scale':1.0, 'lm_cfg_scale':2.5,
        'lm_negative_prompt': (song.exclude_styles or DEFAULT_NEGATIVE)[:2000],
        'seed':secrets.randbelow(2147483647),
    }


def _run(args:list[str], timeout:int, notice:Callable[[str],None]):
    notice('Running ' + Path(args[0]).name + ' ...')
    p = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       stdin=subprocess.DEVNULL, timeout=timeout, check=False)
    if p.returncode:
        raise RuntimeError(f'{Path(args[0]).name} failed ({p.returncode}): {(p.stderr or p.stdout)[-1000:]}')


def _server_audio(req:dict, conf:MusicConfig, target:Path, notice):
    url=conf.server_url.rstrip('/')
    if not url.startswith(('http://127.0.0.1:', 'http://localhost:', 'https://')):
        raise ValueError('Use a localhost SSH tunnel for remote ACE servers')
    notice('Sending approved lyrics and music caption to ACE-Step...')
    payload=json.dumps(req).encode('utf-8')
    first=urllib.request.Request(url+'/lm', data=payload, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(first, timeout=600) as r:
        enriched=json.load(r)
    if not isinstance(enriched, list) or len(enriched)!=1 or not isinstance(enriched[0],dict):
        raise RuntimeError('ACE-Step /lm did not return exactly one enriched request')
    # A model may attempt to rewrite supplied lyrics. Preserve user-approved text and creative direction.
    enriched[0].update({'lyrics':req['lyrics'], 'caption':req['caption']})
    notice('Synthesizing instrumentation and vocals through ACE-Step...')
    second=urllib.request.Request(url+'/synth?wav=1', data=json.dumps(enriched[0]).encode('utf-8'),
                                  headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(second, timeout=1800) as r, target.open('wb') as out:
        content_type=r.headers.get('Content-Type','').lower()
        if 'audio/' not in content_type and 'octet-stream' not in content_type:
            raise RuntimeError(f'ACE-Step returned unexpected audio response {content_type}')
        bytes_read=0
        while True:
            part=r.read(1024*1024)
            if not part:break
            bytes_read+=len(part)
            if bytes_read>700*1024*1024:
                raise ValueError('Generated audio exceeds maximum supported size')
            out.write(part)
    if target.stat().st_size<4096:
        raise RuntimeError('ACE-Step returned an empty or truncated audio file')


def _cli_audio(req:dict, conf:MusicConfig, target:Path, notice):
    lm=check_tool(conf.lm_executable)
    synth=check_tool(conf.synth_executable)
    models=Path(conf.model_dir).expanduser().resolve()
    if not models.is_dir():
        raise FileNotFoundError(f'ACE model directory not found: {models}')
    base=target.parent/'request.json'
    base.write_text(json.dumps(req), encoding='utf-8')
    _run([lm,'--models',str(models),'--request',str(base),'--device',conf.device],300,notice)
    stage=base.with_name('request0.json')
    if not stage.is_file():
        raise RuntimeError('ACE-Step language stage did not create request0.json')
    _run([synth,'--models',str(models),'--request',str(stage),
          '--device',conf.device,'--vae-chunk','128','--vae-overlap','32'],1200,notice)
    produced=stage.with_name('request00.mp3')
    if not produced.is_file():
        raise RuntimeError('ACE-Step synthesis stage did not create request00.mp3')
    if produced.stat().st_size < 4096:
        raise RuntimeError('ACE-Step produced an empty audio file')
    shutil.copyfile(produced,target)


def convert_audio(source:Path, output:Path, fmt:str, ffmpeg:str='ffmpeg', ffprobe:str='ffprobe') -> dict:
    if fmt not in FORMATS:
        raise ValueError(f'Unsupported format {fmt}')
    source=Path(source); output=Path(output)
    if not source.is_file() or source.stat().st_size < 4096:
        raise FileNotFoundError('No valid rendered audio to export')
    command=[check_tool(ffprobe), '-v','error','-show_entries','format=duration:stream=codec_type',
             '-of','json',str(source)]
    scan=subprocess.run(command, capture_output=True, text=True, timeout=20,check=True)
    report=json.loads(scan.stdout)
    duration=float((report.get('format') or {}).get('duration') or 0)
    if duration<10 or not any(s.get('codec_type')=='audio' for s in report.get('streams',[])):
        raise ValueError('Rendered file does not contain valid audio')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='music-export-',dir=str(output.parent)) as scratch:
        candidate=Path(scratch)/('encoded.'+fmt)
        subprocess.run([check_tool(ffmpeg),'-hide_banner','-loglevel','error','-nostdin','-y',
                        '-i',str(source),'-map','0:a:0','-vn',*FORMATS[fmt],str(candidate)],
                       timeout=300,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        if candidate.stat().st_size < 4096:
            raise RuntimeError('FFmpeg produced an incomplete file')
        os.replace(candidate,output)
    return {'path':str(output),'duration_seconds':round(duration,1),'format':fmt}


def generate_song(song:SunoPackage, conf:MusicConfig, directory:str|Path,
                  progress:Callable[[str],None]|None=None) -> dict:
    notice=progress or (lambda _: None)
    if not _AUD_LOCK.acquire(blocking=False):
        raise RuntimeError('An audio render is already in progress; finish the current track first')
    try:
        destination=Path(directory).expanduser()
        destination.mkdir(parents=True, exist_ok=True)
        req=make_ace_request(song,conf)
        fmt=conf.output_format.lower()
        if fmt not in FORMATS:raise ValueError('Unknown audio export format')
        title=safe_song_filename(conf.filename or song.title)
        output=destination/(title+'.'+fmt)
        if output.exists():
            raise FileExistsError(f'{output} already exists; rename the track or choose another folder')
        with tempfile.TemporaryDirectory(prefix='music-synth-') as tmp:
            encoded=Path(tmp)/('recording.wav' if conf.mode=='server' else 'recording.mp3')
            if conf.mode=='server':_server_audio(req,conf,encoded,notice)
            elif conf.mode=='cli':_cli_audio(req,conf,encoded,notice)
            else:raise ValueError('Unknown ACE-Step backend')
            notice('Inspecting and exporting audio with FFmpeg...')
            result=convert_audio(encoded,output,fmt,conf.ffmpeg,conf.ffprobe)
        meta=output.with_suffix(output.suffix+'.recipe.json')
        meta.write_text(json.dumps({'song':song.title,'request':req,'format':fmt,'backend':conf.mode,
                                    'reviewed_lyrics':song.lyrics,'style':song.style},indent=2),encoding='utf-8')
        result['recipe']=str(meta)
        notice('Audio complete: '+str(output))
        return result
    finally:
        _AUD_LOCK.release()
