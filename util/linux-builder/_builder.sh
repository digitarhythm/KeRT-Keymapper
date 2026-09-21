#!/bin/bash

set -e

export LD_LIBRARY_PATH=/vial-gui/util/python36/prefix/lib/

cd /vial-gui
./util/python36/prefix/bin/python3 -m venv docker_venv
. docker_venv/bin/activate
pip install -r requirements.txt
fbs freeze
fbs installer
deactivate
/pkg2appimage-*/pkg2appimage misc/KeRT-mapper.yml
mv out/KeRT-mapper-*.AppImage /output/KeRT-mapper-x86_64.AppImage
