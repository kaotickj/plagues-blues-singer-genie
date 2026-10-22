# Plague's Music Studio

**Plague's Music Studio** is a local-first, Python/PyQt6 application for composing, curating and producing **original blues and metal**. Version **0.3.2** adds genre-specific writing directions and generation-history controls. No cloud AI API subscription is required.

## Genre presets

The **Genre / Style** selector includes:

- **Blues** (general), **Swamp Blues**, **Delta Blues**, **Chicago Blues**, **Whiskey Blues**, **Smoky Blues**.
- **Metal** (general), **Swamp Metal**, **Death Metal**, **Glam Metal**, **Hair Metal**.

Each preset defines appropriate BPM ranges, grooves, instrumental combinations, lead-vocal delivery, arrangement approaches, studio-production ideas, exclusions and stylistic rules. They are boundaries rather than rigid formulas: **Shuffle creative direction** selects a new story seed, narrative perspective, concrete detail, tempo, groove, instrument palette, vocal character, arrangement and recording approach. Artist-specific variation history is saved in SQLite to avoid repeating the most recent themes/grooves/arrangements. The creative brief can override these suggestions. The software cannot guarantee absolute originality or similarity avoidance; human review remains necessary.

For **Swamp Blues**, a recognizable *jaw harp* remains in the chosen instrumentation, but other textures rotate. For **Death Metal**, the model receives harsh-vocal and rhythmic vocabulary, and the independent critic checks metal authenticity rather than blues metrics.

## Features

- **Stage Name Lab:** offline SQLite-based weighted name components and scripted permutations; edit entries and template patterns in the Word Bank, now including a starting metal-oriented vocabulary. No model required.
- **Songwriting & Albums:** artist biographies, style guides, album concepts, three-album planning, complete tagged lyrics, Suno-style prompts and website promotional copy.
- **Four-role local AI curation:** Research (model knowledge only), Draft, Edit and Audit. Assign local Ollama models independently per role. A scored genre-specific quality gate revises the draft up to the configured limit. Failed audits are not approved for audio production.
- **Suno Custom Mode:** separately copy **Tagged Lyrics**, **Style of Music**, and **Exclude Styles**. The section/delivery instructions in brackets go inside the lyrics field. Suno may not interpret every bracketed cue deterministically.
- **Music Production:** when separately installed, connect to ACE-Step via a local/private server API or to the Goodneighbor Blues `ace-lm`/`ace-synth` Vulkan CLI; export generated music and vocals to MP3, WAV, FLAC, OGG or M4A with separately installed FFmpeg and FFprobe. A successful model connection and render are required; merely discovering model weights does not confirm a working engine.
- **Model Manager:** locate executables, standard and Goodneighbor Blues model directories, read installed Ollama manifests without starting an engine, browse for additional model stores, connect to an already running Ollama service (including Docker or SSH tunnels), or install a checksum-verified user-owned Ollama runtime. The app now lets you choose an existing writable model store for the private Ollama process, shows pull/download progress and errors, and supports importing local GGUF models. Non-Ollama GGUF and ACE-Step files are not automatically available as Ollama text models.

## Install from source

Python 3.12 or later is recommended. On Debian:

```bash
sudo apt install python3-venv libegl1 libgl1 libxkbcommon0 libxcb-cursor0
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows, create a Python virtual environment, install `requirements.txt`, and launch `python main.py`. For **Ollama**, the default API is `http://127.0.0.1:11434`. When the model engine is hosted on your Goodneighbor Blues Linux server, prefer an SSH tunnel rather than publishing model APIs on the LAN or internet:

```bash
ssh -N -L 11435:127.0.0.1:11434 YOUR_GOODNEIGHBOR_SSH_ALIAS
```

Set the studio's Ollama URL to `http://127.0.0.1:11435`. The historical Windows `PlaguedAI` model paths belong to the original main PC, **not** the Linux server. For production use, verify server-side model locations and permissions instead of assuming path equivalence.

## Installers: Windows and Linux

Both GitHub Actions workflows run the unit tests. Linux additionally smoke-tests the frozen GUI headlessly and creates a `.deb` using native Debian packaging tools. Windows produces a PyInstaller executable with an Inno Setup installer. Neither installer bundles Ollama weights, ACE-Step binaries, or FFmpeg; users may install/locate them with the Model Manager or configure separate services.

- [Windows installer workflow](https://github.com/kaotickj/plagues-blues-singer-genie/actions/workflows/windows.yml)
- [Linux `.deb` installer workflow](https://github.com/kaotickj/plagues-blues-singer-genie/actions/workflows/linux.yml)

Install the Linux artifact after extracting the GitHub Actions ZIP:

```bash
sudo apt install ./plagues-music-studio_0.3.2_amd64.deb
plagues-music-studio
```

The GitHub repository's existing URL remains `kaotickj/plagues-blues-singer-genie` until its owner renames the repository; **application and package branding** have changed independently.

## Model manager troubleshooting

The Music Studio installable GUI is **not** itself an AI engine. You need a running Ollama service for text and a separately running ACE-Step CLI/API for audio.

On your Linux machine, first test the service **outside** the app:

```bash
command -v ollama
ollama list
curl --max-time 5 -fsS http://127.0.0.1:11434/api/tags
```

If a Docker container hosts Ollama on the Goodneighbor server, try this **on that server**:

```bash
docker ps --filter name=gnb-ollama
docker exec gnb-ollama ollama list
sudo ls -la /var/lib/gnb-ollama/models/manifests
```

The known Goodneighbor server mounts `/var/lib/gnb-ollama` into Docker as `/root/.ollama`, so the host's Ollama model store is usually `/var/lib/gnb-ollama/models`, **not** the app's user directory. The audio synthesizer's model directory is separately configured as `/var/lib/gnb-song-audio/models`. The account running Music Studio may not have permission to read these host directories. **Do not change their ownership or recursively chmod them** just to make the GUI scan them. Instead, use the already running Ollama API.

When Music Studio is on a different computer, forward the server-side loopback API to your local workstation:

```bash
ssh -N -L 11435:127.0.0.1:11434 YOUR_SERVER_SSH_ALIAS
```

Set Music Studio → AI Settings → Ollama URL to `http://127.0.0.1:11435`, and choose **Connect to configured Ollama URL** under Model Manager. The Music Studio cannot discover remote model files by scanning local disks.

To install on a fresh workstation, use **Install verified Ollama**. It downloads the official (large) runtime into the current user's app data, checks its SHA-256 digest, and starts an isolated Ollama service on port 11535. Use **Download model** with a model tag such as `qwen3:4b` to pull weights into that running instance. Logs and progress appear in Model Manager; a managed-process log is written to the application's local data directory. You do not need to reinstall Ollama or duplicate weights if a working server already exists.

**Audio generation** uses a separate ACE-Step model backend; its GGUF weights are not loadable through Ollama's text-model management. The app verifies configured ACE-Step + FFmpeg in the Music Production tab, but it does **not** yet automatically install the ACE-Step engine.

## Data preservation on upgrade

The new local data directory is `PlaguesMusicStudio` under `%LOCALAPPDATA%` (Windows) or `~/.local/share/` (Linux). On first run, if the new files don't exist, the app copies previous settings and uses SQLite backup to migrate the existing `PlaguesBluesSingerGenie/library.sqlite3`. It leaves original files untouched. Preserve a copy of your library before reinstalling, especially if the application was configured with custom locations.

## Safety and commercial use

Generated identities and biographies are fictional. Review outputs for prior song similarity, trademark conflicts, appropriate rights and model restrictions before release. All local AI model calls send prompts to the configured endpoint. Do not expose unauthenticated model APIs directly. Review the [MIT license](LICENSE) and [third-party licensing notes](THIRD_PARTY_NOTICES.md); PyQt6 and optional model weights have separate terms. A project's MIT source-code license does not relicense third-party code or model weights.

To run tests:

```bash
python -m unittest discover -s tests -v
```

Sponsorship details are in `.github/FUNDING.yml`.

## Distinct tracks within a coherent album

Each of the eleven genre profiles now rotates a genre-appropriate **song form**, **hook device**,
**harmonic palette** and **emotional progression**, in addition to tempo, story, point of view,
instruments, voice, arrangement and production. The selected direction is previewed with
**Shuffle creative direction**. Saved variation history helps avoid recent combinations.

When lyrics are generated for a selected artist, the app also consults that artist's
saved song titles and short chorus/refrain excerpts as **negative examples** for the
drafting, editing and auditing stages. Exact matching titles or refrains fail the
quality gate and trigger bounded revision. Keep the same artist selected while building
an album to use that history. The genre presets are boundaries, not repeated templates;
a human must still review musical quality and originality.
