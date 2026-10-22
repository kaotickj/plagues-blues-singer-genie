#!/usr/bin/env bash
# Package an existing PyInstaller --onedir output as a Debian package.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name='plagues-music-studio'
version="${APP_VERSION:-0.3.2}"
arch="$(dpkg --print-architecture)"
dist="${DIST_DIR:-${root}/dist/PlaguesMusicStudio}"
out="${OUTPUT_DIR:-${root}/installer/output-linux}"
[[ "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([+~][0-9A-Za-z.-]+)?$ ]] || { echo 'Invalid version' >&2; exit 1; }
[[ -x "${dist}/PlaguesMusicStudio" ]] || { echo 'Build the executable first' >&2; exit 1; }
mkdir -p "${out}"
stage="$(mktemp -d)"; trap 'rm -rf "${stage}"' EXIT
mkdir -p "${stage}/DEBIAN" "${stage}/usr/lib/${name}" "${stage}/usr/bin" "${stage}/usr/share/applications" "${stage}/usr/share/doc/${name}"
cp -a "${dist}/." "${stage}/usr/lib/${name}/"
cat > "${stage}/DEBIAN/control" <<CONTROL
Package: ${name}
Conflicts: plagues-blues-singer-genie
Replaces: plagues-blues-singer-genie
Version: ${version}
Section: sound
Priority: optional
Architecture: ${arch}
Maintainer: Kaotick Jay <noreply@github.com>
Depends: libc6 (>= 2.35), libgl1, libegl1, libxkbcommon0, libxcb1, libxcb-cursor0, libxcb-shape0
Description: Local-first blues and metal songwriting and music studio
 Desktop app featuring offline name creation, local model management,
 structured AI curation, Suno prompts and optional ACE-Step audio synthesis.
CONTROL
cat > "${stage}/usr/bin/${name}" <<'SH'
#!/bin/sh
exec /usr/lib/plagues-music-studio/PlaguesMusicStudio "$@"
SH
chmod 0755 "${stage}/usr/bin/${name}"
cat > "${stage}/usr/share/applications/${name}.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Plague's Music Studio
GenericName=Blues and Metal Songwriting and Music Studio
Exec=plagues-music-studio
Icon=multimedia-player
Terminal=false
Categories=AudioVideo;Audio;Utility;
StartupNotify=true
DESKTOP
cp "${root}/LICENSE" "${stage}/usr/share/doc/${name}/copyright"
cp "${root}/THIRD_PARTY_NOTICES.md" "${stage}/usr/share/doc/${name}/third-party-notices.md"
find "${stage}/usr" -type d -exec chmod 0755 {} +
dpkg-deb --build --root-owner-group "${stage}" "${out}/${name}_${version}_${arch}.deb"
echo "Created ${out}/${name}_${version}_${arch}.deb"
