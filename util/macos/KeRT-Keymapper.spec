# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
#
# PyInstaller spec for a native macOS Vial.app. The architecture comes from the
# VIAL_ARCH environment variable ("arm64" or "x86_64", default: the running machine)
# and must match the Python interpreter running PyInstaller: pip wheels are single-arch,
# so an arm64 Python builds arm64 and an x86_64 Python (Intel runner) builds x86_64.
# Run through util/macos/build.sh; see README.md there.
import os
import platform

ARCH = os.environ.get("VIAL_ARCH", platform.machine())
if ARCH not in ("arm64", "x86_64"):
    raise SystemExit("VIAL_ARCH must be arm64 or x86_64, got {!r}".format(ARCH))

ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
SRC = os.path.join(ROOT, "src", "main", "python")
ICON = os.path.join(ROOT, "target", "macos-" + ARCH, "KeRT-Keymapper.icns")
# PyQt5 5.15.11 wheels: macosx_11_0_arm64 / macosx_10_13_x86_64
MIN_OS = "11.0" if ARCH == "arm64" else "10.13"

a = Analysis(
    [os.path.join(SRC, "main.py")],
    pathex=[SRC],
    binaries=[],
    # fbs_runtime resolves resources from Contents/Resources of the bundle
    datas=[(os.path.join(ROOT, "src", "main", "resources", "base"), ".")],
    hiddenimports=["hid"],
    hookspath=[],
    runtime_hooks=[os.path.join(SPECPATH, "rthook_fbs_build_settings.py")],
    excludes=["PyQt5.QtQml", "PyQt5.QtQuick", "PyQt5.QtWebEngine", "PyQt5.QtWebEngineWidgets",
              "PyQt5.QtMultimedia", "PyQt5.QtBluetooth", "PyQt5.QtLocation", "PyQt5.QtPositioning",
              "PyQt5.Qt3DCore", "PyQt5.QtDesigner", "PyQt5.QtHelp", "PyQt5.QtSql", "PyQt5.QtTest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="KeRT-Keymapper",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=ARCH,
    icon=ICON if os.path.exists(ICON) else None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="KeRT-Keymapper")
app = BUNDLE(
    coll,
    name="KeRT-Keymapper.app",
    icon=ICON if os.path.exists(ICON) else None,
    bundle_identifier="io.github.digitarhythm.kert-keymapper",
    info_plist={
        "CFBundleName": "KeRT-Keymapper",
        "CFBundleDisplayName": "KeRT-Keymapper",
        "CFBundleShortVersionString": "1.1.2",
        "CFBundleVersion": "1.1.2",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": MIN_OS,
    },
)
