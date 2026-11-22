#!/usr/bin/env bash
set -euo pipefail
version=5.3.0
archive="blender-$version-linux-x64.tar.xz"
checksum=dacb8264197a3f7fda6001285a5a506fc97ee943881261c2c3bd63c882f22e05
folder="${RUNNER_TEMP:-/tmp}/fitness-blender-$version"
mkdir -p "$folder"
partial="$folder/$archive.part"
success=false
for mirror in https://download.blender.org/release https://ftp.halifax.rwth-aachen.de/blender/release; do
  if curl --fail --location --proto '=https' --proto-redir '=https' --connect-timeout 20 \
      --max-time 600 --retry 3 "$mirror/Blender5.3/$archive" -o "$partial" &&
      printf '%s  %s\n' "$checksum" "$partial" | sha256sum -c -; then
    success=true
    break
  fi
done
if [[ "$success" != true ]]; then echo 'Verified Blender 5.3 download failed' >&2; exit 1; fi
tar -xf "$partial" --strip-components=1 -C "$folder"
rm "$partial"
"$folder/blender" --version
printf 'FITNESS_BLENDER=%s/blender\n' "$folder" >> "${GITHUB_ENV:?}"
