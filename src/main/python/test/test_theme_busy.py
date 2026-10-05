# SPDX-License-Identifier: GPL-2.0-or-later
"""Picking a theme in the Theme menu: a translucent black cover with a loading spinner in the middle stays
over the window while the theme is applied, and goes before the "reload / restart" message
(docs/theme-menu-spec.md)."""
import os
import sys
import types

from PyQt5.QtGui import QColor

sys.path.insert(0, os.path.dirname(__file__))


def window(qtbot, monkeypatch):
    import branding_theme
    from test_gui import prepare, FAKE_KEYBOARD
    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    # no writes to the real settings, no modal message box in the tests
    monkeypatch.setattr(branding_theme, "save_theme", lambda settings, name, web=None: None)
    messages = []
    monkeypatch.setattr(mw, "show_theme_message", lambda: messages.append(mw.busy_overlay_shown()))
    return mw, messages


def test_cover_while_the_theme_is_applied(qtbot, monkeypatch):
    import themes
    mw, messages = window(qtbot, monkeypatch)
    applied = []
    original = themes.Theme.set_theme.__func__
    monkeypatch.setattr(themes.Theme, "set_theme",
                        classmethod(lambda cls, name: (applied.append((name, mw.busy_overlay_shown())),
                                                       original(cls, name))))
    try:
        mw.set_theme("Dark")
        assert mw.busy_overlay_shown(), "the cover comes at once"
        assert applied == [], "the theme is applied a moment later, once the cover shows"
        qtbot.waitUntil(lambda: bool(messages), timeout=3000)
        assert applied == [("Dark", True)], "applied under the cover"
        assert messages == [False], "the cover is gone when the message comes"
    finally:
        original(themes.Theme, "KeRT Color")


def test_cover_is_translucent_black_with_a_spinner(qtbot, monkeypatch):
    from widgets.busy_overlay import BusyOverlay
    mw, messages = window(qtbot, monkeypatch)
    before = mw.grab().toImage()
    cover = BusyOverlay(mw)
    cover.show()
    assert cover.geometry() == mw.rect(), "over the whole window"
    img = mw.grab().toImage()
    corner_before, corner = QColor(before.pixel(30, mw.height() - 30)), QColor(img.pixel(30, mw.height() - 30))
    assert corner.lightness() < corner_before.lightness() - 20, "darkened"
    assert corner.lightness() > 0 or corner_before.lightness() == 0, "translucent, not solid black"
    # the spinner: light pixels on a ring around the centre
    cx, cy = mw.width() // 2, mw.height() // 2
    r = cover.SPINNER_RADIUS
    ring = [QColor(img.pixel(cx + dx, cy + dy)) for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r))]
    assert any(c.lightness() > 150 for c in ring), "a light spinner arc on the ring"
    cover.close()


def test_web_cover_is_drawn_by_the_page(qtbot, monkeypatch):
    """In the browser the page draws the cover and the spinner (vialglue.busy): it keeps turning while
    the worker is busy applying the theme"""
    from widgets import busy_overlay
    sent = []
    monkeypatch.setitem(sys.modules, "vialglue", types.SimpleNamespace(busy=sent.append))
    mw, messages = window(qtbot, monkeypatch)
    busy_overlay.set_busy(mw, True, web=True)
    assert sent == [1] and not mw.busy_overlay_shown()
    busy_overlay.set_busy(mw, False, web=True)
    assert sent == [1, 0]
