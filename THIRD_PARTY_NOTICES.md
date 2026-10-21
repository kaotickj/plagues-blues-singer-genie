# Third-party components and licenses

Plague's Music Studio source code is licensed under the MIT License in `LICENSE`.

**The standard Windows and Linux installers contain neither AI model weights nor Ollama, FFmpeg, or ACE-Step executables.** The in-app runtime installer fetches a user-approved official Ollama binary release, verifies its published SHA-256 checksum, then extracts it into the current user's own application-data directory. The app can use a pre-existing Ollama installation instead.

- **PyQt6**, Qt libraries and packaging dependencies have their own licenses. Check the installed PyQt6, Qt and PyInstaller distributions for redistribution terms. Qt/PyQt's GPL/commercial options are **not relicensed by our MIT license**. For proprietary distribution, obtain applicable licensing advice or use a compatible licensed binding.
- **Ollama**: See https://github.com/ollama/ollama/blob/main/LICENSE. The managed runtime remains a separately supplied third-party binary; verify its current release notices before redistribution.
- **FFmpeg / FFprobe**: https://ffmpeg.org/legal.html. FFmpeg build licensing depends on compile-time options. The app currently discovers an existing executable on the user's system; it does not redistribute FFmpeg. Users are responsible for selecting a license-compliant build.
- **ACE-Step** and `ace.cpp`: https://github.com/ace-step/ACE-Step and https://github.com/ace-step/acestep.vst3. Verify licenses and model weight terms for the specific executable and weights used. The application invokes separately installed tools or a private service.
- **AI model weights**: Some model licenses restrict commercial use, redistribution, or generated content. This repository neither bundles nor grants licenses to third-party weights. Always review the terms for the selected models and output.

Sponsorship links are voluntary and do not grant additional software rights.
