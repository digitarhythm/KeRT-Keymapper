#!/bin/bash
# Build the browser version on this machine. Output: web/src/build, which web/dev_server.py serves
# automatically (restart it after a build). See web/README.md.
#
# Linux: runs the build scripts directly (like CI).
# macOS: runs them in an Ubuntu 22.04 Docker container (OrbStack / Docker Desktop), because the
#   Command Line Tools cannot build Qt's host tools. The container works in <repo>/web-linux, a copy of
#   the build scripts next to web/, so that the app sources resolve the same way as in CI; the toolchain
#   and dependency builds are kept there between runs (first run 30-40 minutes, later runs a few minutes).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)

run_build() {   # in $1 (a web/ directory), with the scripts' Linux assumptions
    cd "$1"
    [ -d emsdk ] || ./fetch-emsdk.sh
    [ -d sources ] || ./fetch-deps.sh
    [ -f deps/PyQt5-*/QtSvg/libQtSvg.a ] || ./build-deps.sh
    [ -d via-keymap-precompiled ] || git clone --depth 1 https://github.com/vial-kb/via-keymap-precompiled.git
    cd src && ./build.sh
}

if [ "$(uname)" = "Linux" ]; then
    run_build "$HERE"
    echo "done: $HERE/src/build"
    exit 0
fi

# KERT_LINUX_PLATFORM: linux/amd64 (default; the CI's architecture) or linux/arm64 (native on Apple Silicon,
# needs EMSDK_VERSION >= 3.1.45 because older emscripten has no Linux arm64 binaries)
PLATFORM=${KERT_LINUX_PLATFORM:-linux/amd64}
LINUX_DIR="$ROOT/web-linux-${PLATFORM##*/}"

if [ -n "$KERT_IN_CONTAINER" ]; then
    run_build "$KERT_LINUX_DIR"
    exit 0
fi

command -v docker >/dev/null || { echo "docker is required on macOS (OrbStack or Docker Desktop)"; exit 1; }
# copy the build scripts (not the toolchain / build output) next to web/
mkdir -p "$LINUX_DIR"
rsync -a --delete --exclude emsdk --exclude sources --exclude deps --exclude build --exclude via-keymap-precompiled \
      --exclude .preview --exclude .macos-bin --exclude __pycache__ \
      "$HERE/" "$LINUX_DIR/" --exclude 'src/build' \
      --filter='protect emsdk' --filter='protect sources' --filter='protect deps' --filter='protect via-keymap-precompiled' --filter='protect src/build'
# x86_64 even on Apple Silicon (Rosetta / QEMU): emscripten 3.1.10 has no Linux arm64 binaries
docker build -q --platform "$PLATFORM" -t "kert-keymapper-webbuild-${PLATFORM##*/}" -f "$HERE/Dockerfile.build" "$HERE" >/dev/null
docker run --rm --platform "$PLATFORM" -e KERT_IN_CONTAINER=1 -e "KERT_LINUX_DIR=/work/$(basename "$LINUX_DIR")" -e EMSDK_VERSION \
    -v "$ROOT:/work" -w "/work/$(basename "$LINUX_DIR")" "kert-keymapper-webbuild-${PLATFORM##*/}" bash "/work/$(basename "$LINUX_DIR")/build-local.sh"
rm -rf "$HERE/src/build"
cp -R "$LINUX_DIR/src/build" "$HERE/src/build"
echo "done: $HERE/src/build (built in Docker from $LINUX_DIR)"
