# SPDX-License-Identifier: GPL-2.0-or-later
"""The KKM app icon follows the grey scheme (2026-09-27): light grey face (the highlight grey), black
letters with the logo's grey rim, dark frame; no KeRT green in any size (docs/app-icon-spec.md)."""
import glob
import os

import pytest
from PyQt5.QtGui import QColor, QImage, QImageReader

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../../.."))
PNGS = sorted(glob.glob(os.path.join(ROOT, "src/main/icons/*/*.png"))) + [os.path.join(ROOT, "web/src/icon.png")]


def opaque_colours(img):
    seen = {}
    step = max(1, img.width() // 128)
    for y in range(0, img.height(), step):
        for x in range(0, img.width(), step):
            c = QColor.fromRgba(img.pixel(x, y))
            if c.alpha() == 255:
                seen[c.name()] = seen.get(c.name(), 0) + 1
    return seen


def achromatic(name):
    c = QColor(name)
    return abs(c.red() - c.green()) <= 3 and abs(c.green() - c.blue()) <= 3


@pytest.mark.parametrize("path", PNGS, ids=lambda p: os.path.relpath(p, ROOT))
def test_icon_png_is_grey(qtbot, path):
    img = QImage(path)
    assert not img.isNull() and img.width() == img.height()
    colours = opaque_colours(img)
    assert colours and all(achromatic(n) for n in colours), "no coloured pixels"
    # the face is the light highlight grey
    assert max(colours, key=colours.get) == "#cccccc"


def test_ico_is_grey(qtbot):
    reader = QImageReader(os.path.join(ROOT, "src/main/icons/Icon.ico"))
    assert reader.imageCount() == 7
    for i in range(reader.imageCount()):
        reader.jumpToImage(i)
        img = reader.read()
        assert not img.isNull()
        assert all(achromatic(n) for n in opaque_colours(img))


def test_face_matches_the_highlight(qtbot):
    from PyQt5.QtGui import QPalette
    import branding_theme
    img = QImage(os.path.join(ROOT, "src/main/icons/mac/1024.png"))
    assert QColor(img.pixel(512, 150)).name() == dict(branding_theme.BRAND_THEMES)["KeRT Light"][QPalette.Highlight]
