#!/bin/bash

set -e

# EMSDK_VERSION overrides the emscripten version (default 3.1.10, the version the Qt/CPython patches
# were made for); a newer version uses the current emsdk checkout instead of the pinned one.
EMSDK_VERSION=${EMSDK_VERSION:-3.1.10}
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
if [ "$EMSDK_VERSION" = "3.1.10" ]; then git checkout 891b4491419c42f9d2b9f97c47d1043b26dfd3e5; fi
./emsdk install $EMSDK_VERSION
./emsdk activate $EMSDK_VERSION
cd ..
