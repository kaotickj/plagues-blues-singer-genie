# Plague's Blues Singer Genie

A local-first, fictional blues artist development studio for **real-world blues**, powered by Python and PyQt6.

## Version 0.1.0

- Generate original blues stage-name suggestions **offline**, including presentation and genre controls.
- Discover installed Ollama **text** models at runtime, including Gemma 3 / Qwen 3 if they are loaded by your Ollama server.
- Generate AI stage names, artist biographies, consistent artist style guides, album concepts (including a three-album batch), original song lyrics, Suno production prompts, and promotional copy.
- Save artists, biographies, and generated drafts to a local SQLite library.
- Edit generated text before saving. Persistent settings live in the user's app-data directory.
- Windows GitHub Actions builds a PyInstaller application and Inno Setup installer.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Start Ollama separately on the local computer. Open **AI Settings**, enter an Ollama base URL (default `http://127.0.0.1:11434`), choose **Discover installed Ollama models**, then select a **text** model. `ollama list` is a useful way to check what actually runs. The app connects via `/api/tags` and `/api/generate`; it does **not** read model cache folders or install/delete models. Offline stage-name generation works without Ollama.

Your Chatterbox, Qwen3-TTS, IndexTTS, Kokoro and ACE-Step directories are **not** Ollama text models. Voice and music model execution are intentionally **not implemented in v0.1.0**. This keeps the Windows installer lightweight and avoids bundling GPU frameworks. Future integrations can use dedicated local services.

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
