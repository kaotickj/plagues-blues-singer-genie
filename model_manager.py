"""Local Ollama runtime installation, location, verification and model management.

The managed runtime runs with the user's own permissions; no sudo or shell pipe.
The model manager never deletes user models or replaces system services.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from blues_core import Ollama, paths

API_RELEASE = 'https://api.github.com/repos/ollama/ollama/releases/latest'
USER_AGENT = 'PlaguesMusicStudio/0.3.1'
MANAGED_PORT = 11535
MAX_ARCHIVE = 4 * 1024**3
MODEL_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$')


def app_runtime_dir():
    return paths() / 'ollama-runtime'


def app_models_dir():
    return paths() / 'ollama-models'


def bundled_executable():
    # PyInstaller --onedir: sys.executable is the actual frozen exe in dist/.
    base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    name = 'ollama.exe' if os.name == 'nt' else 'ollama'
    for candidate in (base / 'ollama-runtime' / 'bin' / name,
                      base / 'ollama-runtime' / name,
                      base / '_internal' / 'ollama-runtime' / 'bin' / name):
        if candidate.is_file():
            return candidate
    return None


def known_executables():
    name = 'ollama.exe' if os.name == 'nt' else 'ollama'
    legacy_runtime = paths().parent / 'PlaguesBluesSingerGenie' / 'ollama-runtime'
    candidates = [bundled_executable(), app_runtime_dir() / 'bin' / name, app_runtime_dir() / name,
                  legacy_runtime / 'bin' / name, legacy_runtime / name]
    which = shutil.which('ollama')
    if which:
        candidates.append(Path(which))
    if os.name == 'nt':
        candidates.extend([Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Ollama' / 'ollama.exe',
                           Path(os.environ.get('PROGRAMFILES', '')) / 'Ollama' / 'ollama.exe'])
    else:
        candidates.extend([Path('/usr/local/bin/ollama'), Path('/usr/bin/ollama'), Path('/opt/ollama/bin/ollama')])
    result, seen = [], set()
    for candidate in candidates:
        if candidate:
            p = Path(candidate)
            if str(p) not in seen and p.is_file():
                result.append(p)
                seen.add(str(p))
    return result


def offline_model_tags(store):
    """Discover installed Ollama tags from local manifests; does not prove inference works."""
    manifest_root = Path(store).expanduser() / 'manifests'
    if not manifest_root.is_dir():
        return []
    names = set()
    try:
        for registry in manifest_root.iterdir():
            if not registry.is_dir() or registry.is_symlink():
                continue
            for namespace in registry.iterdir():
                if not namespace.is_dir() or namespace.is_symlink():
                    continue
                for model in namespace.iterdir():
                    if not model.is_dir() or model.is_symlink():
                        continue
                    for tag in model.iterdir():
                        if tag.is_file() and not tag.is_symlink():
                            base = model.name if namespace.name == 'library' else namespace.name + '/' + model.name
                            names.add(base + ':' + tag.name)
    except OSError:
        return []
    return sorted(names)


def known_model_stores(extra_paths=()):
    home = Path.home()
    legacy_models = paths().parent / 'PlaguesBluesSingerGenie' / 'ollama-models'
    candidates = [*extra_paths, app_models_dir(), legacy_models, home / '.ollama' / 'models',
                  home / 'models', home / 'AI' / 'models', home / 'PlaguedAI' / 'models',
                  home / '.cache' / 'huggingface' / 'hub',
                  Path('/var/lib/gnb-ollama/models'), Path('/var/lib/gnb-song-audio/models')]
    for env_name in ('OLLAMA_MODELS','GNB_MODEL_DIR','HF_HOME','HUGGINGFACE_HUB_CACHE'):
        env = os.environ.get(env_name)
        if env:
            candidates.insert(0, Path(env).expanduser() / 'hub' if env_name == 'HF_HOME' else Path(env).expanduser())
    if os.name == 'nt':
        candidates.extend([Path(os.environ.get('USERPROFILE', str(home))) / '.ollama' / 'models',
                           Path(os.environ.get('LOCALAPPDATA', str(home / 'AppData' / 'Local'))) / 'PlaguedAI' / 'models' / 'ollama'])
    else:
        candidates.extend([Path('/usr/share/ollama/.ollama/models'), Path('/var/lib/ollama/.ollama/models')])
    unique, seen = [], set()
    for path in candidates:
        path = Path(path).expanduser()
        if str(path) not in seen and path.is_dir():
            # A store must have manifests or blobs to be considered discovered.
            is_ollama = (path / 'manifests').is_dir() or (path / 'blobs').is_dir()
            tags = offline_model_tags(path) if is_ollama else []
            # Non-Ollama GGUF caches can be imported, but are not Ollama-ready tags.
            gguf = [] if is_ollama else [str(p) for p in path.glob('*.gguf') if p.is_file()][:20]
            unique.append({'path': str(path), 'ollama_store': is_ollama,
                           'models': tags, 'gguf': gguf, 'readable': os.access(path, os.R_OK),
                           'writable': os.access(path, os.W_OK)})
            seen.add(str(path))
    return unique


def check_ollama_api(url, timeout=5):
    url = str(url).strip().rstrip('/')
    if not url.startswith(('http://127.0.0.1:', 'http://localhost:', 'https://')):
        raise ValueError('Use a localhost SSH tunnel or an HTTPS endpoint')
    try:
        return {'url': url, 'models': Ollama(url, timeout=timeout).models()}
    except Exception as exc:
        raise ConnectionError(f'Ollama is unreachable at {url}. Start Ollama, start the private runtime, or establish your server SSH tunnel. Details: {exc}') from exc


def executable_version(executable):
    path = Path(executable)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    p = subprocess.run([str(path), '--version'], capture_output=True, text=True, timeout=15)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f'Exit status {p.returncode}')
    return (p.stdout or p.stderr).strip()


def _get_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def release_asset():
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine not in ('x86_64', 'amd64'):
        raise RuntimeError(f'Only x86-64 runtime installation is supported here: {machine}')
    if system == 'linux':
        filename = 'ollama-linux-amd64.tar.zst'
    elif system == 'windows':
        filename = 'ollama-windows-amd64.zip'
    else:
        raise RuntimeError(f'Unsupported operating system: {system}')
    release = _get_json(API_RELEASE)
    asset = next((a for a in release.get('assets', []) if a.get('name') == filename), None)
    if not asset:
        raise RuntimeError(f'Ollama release has no {filename} asset')
    url = str(asset.get('browser_download_url', ''))
    if not url.startswith('https://github.com/ollama/ollama/releases/download/'):
        raise RuntimeError('Unexpected runtime download source')
    digest = asset.get('digest', '')
    if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
        # Never run an unverified runtime. GitHub release assets advertise digests.
        raise RuntimeError('Ollama release did not provide a SHA-256 digest; installation blocked')
    return url, digest.partition(':')[2].lower(), filename


def _safe_member(name):
    candidate = PurePosixPath(name.replace('\\', '/'))
    if candidate.is_absolute() or '..' in candidate.parts or not candidate.parts or ':' in candidate.parts[0]:
        raise ValueError('Unsafe archive path')
    return candidate


def extract_verified_archive(archive, target, filename):
    """Extract regular files/directories only, with path and size limits."""
    target = Path(target)
    total = 0
    def save_file(name, source, size, executable=False):
        nonlocal total
        rel = _safe_member(name)
        total += size
        if total > 12 * 1024**3:
            raise RuntimeError('Archive uncompressed contents exceed limit')
        out = target.joinpath(*rel.parts)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'wb') as dest:
            shutil.copyfileobj(source, dest, length=1024 * 1024)
        if executable and os.name != 'nt':
            out.chmod(out.stat().st_mode | stat.S_IXUSR)

    if filename.endswith('.zip'):
        with zipfile.ZipFile(archive) as z:
            for m in z.infolist():
                if (m.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
                    raise ValueError('Archive symlinks are not allowed')
                if m.is_dir():
                    continue
                with z.open(m) as src:
                    save_file(m.filename, src, m.file_size)
    else:
        try:
            import zstandard
        except ImportError as e:
            raise RuntimeError('Install Python package zstandard to unpack Linux Ollama') from e
        with open(archive, 'rb') as compressed:
            with zstandard.ZstdDecompressor().stream_reader(compressed) as uncompressed:
                with tarfile.open(fileobj=uncompressed, mode='r|') as tf:
                    for m in tf:
                        if m.isdir():
                            continue
                        if m.issym():
                            # Official Linux releases may contain links inside lib/ollama.
                            out = unpacked_path = target.joinpath(*_safe_member(m.name).parts)
                            if os.path.isabs(m.linkname) or not m.linkname:
                                raise ValueError('Archive contains an unsafe symlink')
                            if not (out.parent / m.linkname).resolve(strict=False).is_relative_to(target.resolve()):
                                raise ValueError('Archive symlink escapes target')
                            out.parent.mkdir(parents=True, exist_ok=True)
                            out.symlink_to(m.linkname)
                            continue
                        if not m.isfile():
                            raise ValueError('Archive contains unsupported link or special file')
                        src = tf.extractfile(m)
                        if src is None:
                            raise ValueError('Could not read archive entry')
                        with src:
                            save_file(m.name, src, m.size, bool(m.mode & 0o111))


def install_managed_runtime(on_progress=None):
    """Install official SHA-256 verified Ollama release in user app-data."""
    report = on_progress or (lambda _: None)
    home = app_runtime_dir()
    if home.exists():
        raise FileExistsError(f'Ollama runtime already installed: {home}. Select the existing executable instead of downloading it again.')
    url, expected, filename = release_asset()
    report(f'Downloading official Ollama package: {filename}; may exceed 1 GB')
    home.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=home.parent) as temp:
        temp_path = Path(temp)
        artifact = temp_path / filename
        sha = hashlib.sha256()
        downloaded = 0
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(request, timeout=120) as source, open(artifact, 'wb') as dest:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > MAX_ARCHIVE:
                    raise RuntimeError('Download exceeds safety limit')
                sha.update(chunk)
                dest.write(chunk)
                if downloaded % (128 * 1024 * 1024) < len(chunk):
                    report(f'Downloaded {downloaded // 1048576} MB')
        if sha.hexdigest() != expected:
            raise RuntimeError('Downloaded runtime SHA-256 did not match published checksum')
        report('Checksum verified. Extracting user-owned runtime...')
        unpacked = temp_path / 'runtime'
        unpacked.mkdir()
        extract_verified_archive(artifact, unpacked, filename)
        name = 'ollama.exe' if os.name == 'nt' else 'ollama'
        candidates = [p for p in unpacked.rglob(name) if p.is_file()]
        if not candidates:
            raise RuntimeError('Verified release has no Ollama executable')
        # Do not overwrite a functioning installation without an explicit removal action.
        if home.exists():
            raise FileExistsError(f'Managed runtime already installed: {home}')
        unpacked.rename(home)
    report(f'Installed Ollama in {home}')
    return str(next(p for p in home.rglob(name) if p.is_file()))


class ManagedRuntime:
    def __init__(self):
        self.process = None
        self.port = MANAGED_PORT

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}'

    def start(self, executable, store=None):
        if self.process is not None and self.process.poll() is None:
            return self.url
        with socket.socket() as test:
            if test.connect_ex(('127.0.0.1', self.port)) == 0:
                raise RuntimeError(f'Port {self.port} already belongs to another process; not taking it over')
        p = Path(executable).expanduser().resolve()
        executable_version(p)
        store = Path(store).expanduser() if store else app_models_dir()
        store.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env['OLLAMA_HOST'] = f'127.0.0.1:{self.port}'
        env['OLLAMA_MODELS'] = str(store.resolve())
        env['OLLAMA_NO_CLOUD'] = '1'
        env['OLLAMA_KEEP_ALIVE'] = '0'
        if os.name != 'nt':
            env['OLLAMA_VULKAN'] = '1'
        env['PATH'] = str(p.parent) + os.pathsep + env.get('PATH', '')
        # Ollama's bundled Linux inference libraries live in lib/ollama.
        lib = p.parent.parent / 'lib' / 'ollama'
        if lib.is_dir() and os.name != 'nt':
            env['LD_LIBRARY_PATH'] = str(lib) + os.pathsep + env.get('LD_LIBRARY_PATH', '')
        self.log_path = paths() / 'managed-ollama.log'
        self.log_handle = open(self.log_path, 'ab')
        try:
            self.process = subprocess.Popen([str(p), 'serve'], env=env, stdout=self.log_handle,
                                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        except Exception:
            self.log_handle.close()
            self.log_handle = None
            raise
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                code = self.process.returncode
                self.process = None
                raise RuntimeError(f'Ollama exited during startup (status {code}); inspect {self.log_path}')
            try:
                Ollama(self.url, timeout=2).models()
                return self.url
            except (ConnectionError, TimeoutError, urllib.error.URLError):
                time.sleep(0.5)
        self.stop()
        raise TimeoutError(f'Ollama did not respond on the managed local port; inspect {self.log_path}')

    def stop(self):
        process, self.process = self.process, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if getattr(self, 'log_handle', None) is not None:
            self.log_handle.close()
            self.log_handle = None


def validate_model_name(name):
    name = name.strip()
    if not MODEL_NAME.fullmatch(name):
        raise ValueError('Model name may contain letters, numbers, dots, dashes, underscores, slashes or colons')
    return name


def pull_model(url, name, progress=None):
    """Stream Ollama model download progress; Ollama handles model validation/cache."""
    name = validate_model_name(name)
    report = progress or (lambda _: None)
    payload = json.dumps({'model': name, 'stream': True}).encode('utf-8')
    req = urllib.request.Request(url.rstrip('/') + '/api/pull', data=payload,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=3600) as response:
        for line in response:
            if not line.strip():
                continue
            update = json.loads(line)
            if update.get('error'):
                raise RuntimeError(str(update['error']))
            total = update.get('total', 0)
            complete = update.get('completed', 0)
            fraction = f' ({complete * 100 // total}%)' if total else ''
            report(str(update.get('status', 'Downloading')) + fraction)
    return Ollama(url, timeout=30).models()


def verify_model(url, name):
    name = validate_model_name(name)
    response = Ollama(url, timeout=30)._request('/api/show', {'model': name})
    details = response.get('details') or {}
    return {'name': name, 'family': details.get('family', 'unknown'),
            'parameter_size': details.get('parameter_size', 'unknown'),
            'format': details.get('format', 'unknown'),
            'capabilities': response.get('capabilities', []),
            'verified': bool(response.get('modelfile') or response.get('details'))}


def import_local_gguf(url, executable, gguf, model_name):
    model_name = validate_model_name(model_name)
    gguf = Path(gguf).expanduser().resolve()
    if not gguf.is_file() or gguf.suffix.lower() != '.gguf':
        raise ValueError('Choose an existing .gguf model file')
    if not Path(executable).is_file():
        raise FileNotFoundError('Locate Ollama executable first')
    # CLI transfers GGUF model from client disk to the selected Ollama instance.
    with tempfile.TemporaryDirectory() as scratch:
        modelfile = Path(scratch) / 'Modelfile'
        modelfile.write_text(f'FROM "{gguf}"\n', encoding='utf-8')
        env = os.environ.copy()
        env['OLLAMA_HOST'] = url.split('://', 1)[-1].rstrip('/')
        completed = subprocess.run([str(executable), 'create', model_name, '-f', str(modelfile)],
                                   capture_output=True, text=True, timeout=3600, env=env)
        if completed.returncode:
            raise RuntimeError((completed.stderr or completed.stdout).strip())
    return verify_model(url, model_name)
