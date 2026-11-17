#!/usr/bin/env bash
set -euo pipefail

version=4.5.16
archive="blender-$version-linux-x64.tar.xz"
checksum=23432b064977908beb1ab4b7f32f024e7331105c875c187dce002aff84b10c11
mode="${1:-}"
archive_dir="${2:-}"

if [[ $# != 2 || ( "$mode" != download && "$mode" != install ) ]]; then
  echo "Usage: $0 {download|install} ARCHIVE_DIRECTORY" >&2
  exit 2
fi

verify_archive() {
  printf '%s  %s\n' "$checksum" "$1" | sha256sum -c - >/dev/null 2>&1
}

if [[ "$mode" == download ]]; then
  mkdir -p "$archive_dir"
  target="$archive_dir/$archive"
  if verify_archive "$target"; then
    exit 0
  fi

  partial=$(mktemp "$archive_dir/.blender-download.XXXXXXXX")
  trap 'rm -f -- "$partial"' EXIT
  mirrors=(
    https://download.blender.org/release
    https://ftp.halifax.rwth-aachen.de/blender/release
    https://ftp.nluug.nl/pub/graphics/blender/release
  )
  for mirror in "${mirrors[@]}"; do
    if ! curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
      --connect-timeout 15 --max-time 180 --retry 2 --retry-max-time 240 \
      "$mirror/Blender4.5/$archive" -o "$partial"; then
      echo "Blender $version download failed from $mirror. Trying the next mirror." >&2
      continue
    fi
    if ! verify_archive "$partial"; then
      echo "Blender $version checksum mismatch from $mirror. Trying the next mirror." >&2
      continue
    fi
    mv -f -- "$partial" "$target"
    exit 0
  done
  echo "Blender $version could not be downloaded and verified from any configured mirror." >&2
  exit 1
fi

if ! verify_archive "$archive_dir/$archive"; then
  echo "The shared Blender $version archive is missing or failed checksum verification." >&2
  exit 1
fi
install_dir=$(mktemp -d "${RUNNER_TEMP:?}/wildlife-blender.XXXXXXXX")
trap 'rm -rf -- "$install_dir"' EXIT
tar -xf "$archive_dir/$archive" --strip-components=1 -C "$install_dir"
version_output=$("$install_dir/blender" --version)
echo "${version_output%%$'\n'*}"
printf 'WILDLIFE_BLENDER=%s/blender\n' "$install_dir" >> "${GITHUB_ENV:?}"
trap - EXIT
