# Plague's Blues Singer Genie

A local-first, fictional blues artist development studio for **real-world blues**, powered by Python and PyQt6.

## Version 0.1.1

- Generate original blues stage-name suggestions **offline**, including presentation and genre controls.
- Discover installed Ollama **text** models at runtime, including Gemma 3 / Qwen 3 if they are loaded by your Ollama server.
- Generate AI stage names, artist biographies, consistent artist style guides, album concepts (including a three-album batch), original song lyrics, Suno production prompts, and promotional copy.
- Save artists, biographies, and generated drafts to a local SQLite library.
- Edit generated text before saving. Persistent settings live in the user's app-data directory.
- GitHub Actions builds Windows (Inno Setup) and Linux (Debian `.deb`) installers.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Start Ollama on the machine actually hosting your language models. Open **AI Settings**, enter an Ollama base URL (default `http://127.0.0.1:11434`), choose **Discover installed Ollama models**, then select a **text** model. `ollama list` is a useful way to check what actually runs. The app connects via `/api/tags` and `/api/generate`; it does **not** read model cache folders or install/delete models. Offline stage-name generation works without Ollama.

Your Chatterbox, Qwen3-TTS, IndexTTS, Kokoro and ACE-Step directories are **not** Ollama text models. Voice and music model execution are intentionally **not implemented in v0.1.1**. This keeps the Windows installer lightweight and avoids bundling GPU frameworks. Future integrations can use dedicated local services.

## Linux installer (Debian / Ubuntu)

The `Linux installer` workflow builds a native `.deb` on Ubuntu 22.04 for x86-64 Linux, runs six unit tests, smoke-tests the PyQt6 app using Qt's offscreen plugin, and uploads the installable package as the `PlaguesBluesSingerGenie-Linux-DEB` Actions artifact. On Debian 13 or Ubuntu, download the artifact and install:

```bash
sudo apt install ./plagues-blues-singer-genie_0.1.1_amd64.deb
plagues-blues-singer-genie
```

You can also launch it from the application menu. Remove with `sudo apt remove plagues-blues-singer-genie`. Your local SQLite data is stored in `~/.local/share/PlaguesBluesSingerGenie/` and survives an uninstall. Model weights are **not bundled**.

To build the Linux installer locally after PyInstaller has produced `dist/PlaguesBluesSingerGenie/`:

```bash
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --clean --noconfirm --windowed --name PlaguesBluesSingerGenie --onedir main.py
APP_VERSION=0.1.1 bash installer/build-linux-deb.sh
```

## Connecting the Goodneighbor Blues model server

The Windows paths under `C:\\Users\\...\\AppData\\Local\\PlaguedAI\\models` are from your **main PC**, not your Linux server. Previously recorded Goodneighbor Blues paths such as `/home/goodneighborblues/site-staging` refer to **website deployment**, not a verified Linux model directory. The actual server-side model root and live Ollama endpoint were not established in earlier chats.

The app connects through Ollama's API, so it needs **the Ollama endpoint, not the weight-file directory**. Keep the endpoint private. When Ollama is installed on a separate Linux host and running on loopback, run this on your desktop (substitute the SSH alias that works on that desktop):

```bash
ssh -N -L 11434:127.0.0.1:11434 YOUR_SSH_HOST_ALIAS
```

Then set `http://127.0.0.1:11434` in AI Settings and click **Discover installed Ollama models**. If local port 11434 is in use, use `-L 11435:127.0.0.1:11434` and set the app URL to `http://127.0.0.1:11435`. On the model server, inspect its actual setup with `ollama list`, `systemctl status ollama`, and `systemctl show ollama -p Environment`. Do not publish port 11434 to the internet.

## Windows builds

Every push to `main` runs tests and packages the app on `windows-latest`. Download the `PlaguesBluesSingerGenie-Windows-Installer` artifact from the successful **Windows installer** Actions run. The built installer is not published as a GitHub Release automatically. Model weights are never bundled.

## Artist consistency

Save a stage name from **Stage Name Lab**. Select the saved artist in **Artist & Album Studio** when creating biographies, style guides, albums and lyrics. Saved biographies are included in subsequent creative prompts. Save changed biographies with **Save artist biography** and other work with **Save to library**. The library is local to the application.

## Scope and cautions

Every generated identity is intended to be fictional. Check stage-name availability, trademarks and similarity to real artists before commercial release. Generated narratives are not claims about real performers. Prompts go only to the configured Ollama endpoint, which can be remote if you explicitly enter a remote URL. Review and edit model outputs before publishing.

## Tests

```bash
python -m unittest discover -s tests -v
```

License: MIT. This project does not contain or redistribute any model weights.
