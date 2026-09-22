# SPDX-License-Identifier: GPL-2.0-or-later
# PyInstaller runtime hook.
#
# `fbs freeze` injects the public build settings (src/build/settings/*.json) into
# fbs_runtime._frozen.BUILD_SETTINGS through a runtime hook of its own. We build
# with plain PyInstaller, so replicate that here; main.py reads app_name / version.
import fbs_runtime._frozen

fbs_runtime._frozen.BUILD_SETTINGS.update({
    "app_name": "KeRT-Keymapper",
    "author": "digitarhythm",
    "version": "1.1.4",
    "mac_bundle_identifier": "io.github.digitarhythm.kert-keymapper",
})
