#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Build a native macOS Vial.app (and .dmg) with PyInstaller for the architecture of the
# Python interpreter in ./venv (arm64 on Apple Silicon, x86_64 on Intel).
#
# Usage: util/macos/build.sh            # architecture = uname -m
#        VIAL_ARCH=x86_64 util/macos/build.sh
#        VIAL_PYTHON=/path/to/python util/macos/build.sh   # use another interpreter than ./venv
#
# Prerequisites: a venv at ./venv created from util/macos/requirements.txt plus
# `pip install --no-deps fbs==0.9.0`. See util/macos/README.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${VIAL_PYTHON:-$ROOT/venv/bin/python}"
ARCH="${VIAL_ARCH:-$(uname -m)}"
OUT="$ROOT/target/macos-$ARCH"

case "$ARCH" in
    arm64|x86_64) ;;
    *) echo "unsupported VIAL_ARCH: $ARCH (expected arm64 or x86_64)" >&2; exit 1 ;;
esac

# pip wheels are single-arch, so the interpreter must already be the target architecture
PY_ARCH="$("$PY" -c 'import platform; print(platform.machine())')"
if [ "$PY_ARCH" != "$ARCH" ]; then
    echo "venv python is $PY_ARCH but VIAL_ARCH is $ARCH; use a $ARCH Python to build" >&2
    exit 1
fi

cd "$ROOT"
mkdir -p "$OUT"

# --- icon: build KeRT-mapper.icns from the PNGs fbs would have used
ICONSET="$OUT/KeRT-mapper.iconset"
rm -rf "$ICONSET" && mkdir -p "$ICONSET"
for size in 16 32 64 128 256 512; do
    sips -z $size $size src/main/icons/mac/1024.png --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z $double $double src/main/icons/mac/1024.png --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$OUT/KeRT-mapper.icns"

# --- freeze
VIAL_ARCH="$ARCH" "$PY" -m PyInstaller --noconfirm --clean \
    --distpath "$OUT/dist" --workpath "$OUT/build" \
    util/macos/KeRT-mapper.spec

# --- sanity check: the main executable must be the requested architecture
lipo -archs "$OUT/dist/KeRT-mapper.app/Contents/MacOS/KeRT-mapper" | grep -qx "$ARCH"

# --- dmg
DMG="$OUT/kert-mapper-mac-$ARCH.dmg"
rm -f "$DMG"
hdiutil create -volname KeRT-mapper -srcfolder "$OUT/dist/KeRT-mapper.app" -ov -format UDZO "$DMG" >/dev/null

echo
echo "arch: $ARCH"
echo "app:  $OUT/dist/KeRT-mapper.app"
echo "dmg:  $DMG"
