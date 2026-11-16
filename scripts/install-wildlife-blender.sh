#!/usr/bin/env bash
set -euo pipefail

version=4.5.16
archive="blender-$version-linux-x64.tar.xz"
scratch=$(mktemp -d)
trap 'unlink "$scratch/$archive"; rmdir "$scratch"' EXIT
curl --fail --silent --show-error --location --retry 4 \
  "https://download.blender.org/release/Blender4.5/$archive" -o "$scratch/$archive"
(
  cd "$scratch"
  echo "23432b064977908beb1ab4b7f32f024e7331105c875c187dce002aff84b10c11  $archive" | sha256sum --check
)
mkdir -p "$RUNNER_TEMP/wildlife-blender"
tar -xf "$scratch/$archive" --strip-components=1 -C "$RUNNER_TEMP/wildlife-blender"
"$RUNNER_TEMP/wildlife-blender/blender" --version | sed -n '1p'
echo "WILDLIFE_BLENDER=$RUNNER_TEMP/wildlife-blender/blender" >> "$GITHUB_ENV"
