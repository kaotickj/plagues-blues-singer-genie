#!/usr/bin/env bash
# Package an existing PyInstaller --onedir output as a native Debian installer.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
app_name="PlaguesBluesSingerGenie"
package_name="plagues-blues-singer-genie"
version="${APP_VERSION:-0.1.1}"
arch="$(dpkg --print-architecture)"
dist_dir="${DIST_DIR:-${repo_root}/dist/${app_name}}"
output_dir="${OUTPUT_DIR:-${repo_root}/installer/output-linux}"

if ! [[ "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([+~][0-9A-Za-z.-]+)?$ ]]; then
  echo "APP_VERSION must be a valid Debian-compatible version: ${version}" >&2
  exit 1
fi

if [[ ! -x "${dist_dir}/${app_name}" ]]; then
  echo "No executable at ${dist_dir}/${app_name}. Build with PyInstaller --onedir first." >&2
  exit 1
fi

mkdir -p "${output_dir}"
stage="$(mktemp -d)"
trap 'rm -rf "${stage}"' EXIT
mkdir -p "${stage}/DEBIAN" "${stage}/usr/lib/${package_name}" "${stage}/usr/bin" \
  "${stage}/usr/share/applications" "${stage}/usr/share/doc/${package_name}"
cp -a "${dist_dir}/." "${stage}/usr/lib/${package_name}/"
cat > "${stage}/DEBIAN/control" <<CONTROL
Package: ${package_name}
Version: ${version}
Section: sound
Priority: optional
Architecture: ${arch}
Maintainer: Plagued Mods <noreply@github.com>
Depends: libc6 (>= 2.35), libgl1, libegl1, libxkbcommon0, libxcb1, libxcb-cursor0
Description: Local-first AI blues artist and album creation studio
 PyQt6 desktop app for blues names, biographies, music styles,
 album concepts, lyrics, Suno prompts, and a persistent artist library.
 Connects to a user-configured Ollama service; includes no model weights.
CONTROL
cat > "${stage}/usr/bin/plagues-blues-singer-genie" <<'LAUNCHER'
#!/bin/sh
exec /usr/lib/plagues-blues-singer-genie/PlaguesBluesSingerGenie "$@"
LAUNCHER
chmod 0755 "${stage}/usr/bin/plagues-blues-singer-genie"
cat > "${stage}/usr/share/applications/plagues-blues-singer-genie.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Plague's Blues Singer Genie
GenericName=Blues Artist Development Studio
Comment=Generate fictional blues artists, albums, and songs with local AI
Exec=plagues-blues-singer-genie
Icon=multimedia-player
Terminal=false
Categories=AudioVideo;Audio;Utility;
StartupNotify=true
DESKTOP
cp "${repo_root}/LICENSE" "${stage}/usr/share/doc/${package_name}/copyright"
find "${stage}/usr" -type d -exec chmod 0755 {} +
chmod 0755 "${stage}/usr/lib/${package_name}/${app_name}"
dpkg-deb --build --root-owner-group "${stage}" \
  "${output_dir}/${package_name}_${version}_${arch}.deb"
echo "Created ${output_dir}/${package_name}_${version}_${arch}.deb"
