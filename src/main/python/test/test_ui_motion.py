# SPDX-License-Identifier: GPL-2.0-or-later
"""Highlight colour and motion (docs/ui-motion-spec.md, 2026-09-27):
- the highlight is a mid grey with white text on it,
- the layer buttons' highlight slides up / down to the chosen layer with an ease curve,
- clicking a tab fades the page out and the new one in, 0.3 s in total."""
import os
import sys

from PyQt5.QtCore import QEasingCurve, QAbstractAnimation, Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QTabWidget

sys.path.insert(0, os.path.dirname(__file__))


def contrast(a, b):
    def lum(c):
        def ch(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---------------------------------------------------------------- highlight colour

def test_highlight_light_with_dark_text(qtbot):
    """ Selected items (tab, layer, key, checked box) are #F0F0F0 with dark text (2026-09-30; #767676
    with white text before): on the black keys, tabs and layer buttons the light one stands out """
    import branding_theme
    import key_style

    theme = dict(branding_theme.BRAND_THEMES)["KeRT Light"]
    hl, hlt = QColor(theme[QPalette.Highlight]), QColor(theme[QPalette.HighlightedText])
    assert hl == QColor("#f0f0f0")
    assert contrast(hl, hlt) >= 7, "dark text on it"
    assert contrast(hl, QColor(key_style.KEY_FACE)) >= 7, "stands out from the black faces"
    svg = open(os.path.join(os.path.dirname(__file__), "../../resources/base/check.svg"), encoding="utf-8").read()
    assert contrast(hl, QColor(svg.split('stroke="')[1].split('"')[0])) >= 4.5, "the check mark reads on it"


# ---------------------------------------------------------------- layer highlight slide

def prepared(qtbot):
    from test_gui import prepare, FAKE_KEYBOARD
    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    mw.resize(1400, 900)
    return mw


def layer_buttons(ke):
    return ke.layer_buttons[:ke.keyboard.layers]


def settled(qtbot, ke):
    """Wait until the layer buttons stop changing: while the window comes up the keyboard is loaded a
    second time (new buttons, back to layer 0) and the column moves into place, so wait for the
    buttons, their geometry and the highlight's geometry to stay the same for 0.3 s"""
    hl = ke.layer_highlight
    last, stable = None, 0
    for _ in range(80):
        qtbot.wait(50)
        b = layer_buttons(ke)
        if not b or not all(x.isVisible() and x.width() > 0 for x in b) or not hl.isVisible():
            last, stable = None, 0
            continue
        snap = (tuple(id(x) for x in b), tuple(x.geometry().getRect() for x in b), hl.geometry().getRect())
        stable = stable + 1 if snap == last else 0
        last = snap
        if stable >= 6:
            break
    b = layer_buttons(ke)
    assert all(x is y for x, y in zip(hl.buttons, b)) and len(hl.buttons) == len(b)
    assert hl.geometry().contains(b[0].geometry()) and hl.geometry().contains(b[-1].geometry())
    return b


def test_layer_highlight_slides(qtbot):
    from widgets.layer_highlight import LayerHighlight

    mw = prepared(qtbot)
    ke = mw.keymap_editor
    hl = ke.layer_highlight
    assert isinstance(hl, LayerHighlight)
    buttons = settled(qtbot, ke)
    # layer buttons are see-through: the fill comes from the sliding highlight behind them
    assert all(b.property("layerButton") for b in buttons)
    assert abs(hl.slide - 0) < 1e-6 and hl.target == 0

    ke.switch_layer(2)
    assert hl.target == 2
    anim = hl.animation
    assert anim.state() == QAbstractAnimation.Running
    assert anim.easingCurve().type() in (QEasingCurve.InOutCubic, QEasingCurve.InOutQuad, QEasingCurve.InOutSine)
    assert 150 <= anim.duration() <= 400
    qtbot.waitUntil(lambda: 0 < hl.slide < 2, timeout=1000)        # on its way
    qtbot.waitUntil(lambda: anim.state() == QAbstractAnimation.Stopped and abs(hl.slide - 2) < 1e-6, timeout=2000)
    # the button under the highlight has white text, the others dark
    assert [b.property("lit") for b in buttons] == [False, False, True, False]


def test_label_white_only_when_covered(qtbot):
    """Halfway between two buttons the box covers neither label: both stay dark"""
    mw = prepared(qtbot)
    ke = mw.keymap_editor
    hl = ke.layer_highlight
    buttons = settled(qtbot, ke)
    hl.animation.stop()
    hl.set_slide(1.5)
    assert [b.property("lit") for b in buttons] == [False, False, False, False]
    hl.set_slide(1.0)
    assert [b.property("lit") for b in buttons] == [False, True, False, False]


def test_layer_highlight_rect_follows_button(qtbot):
    mw = prepared(qtbot)
    ke = mw.keymap_editor
    hl = ke.layer_highlight
    buttons = settled(qtbot, ke)
    ke.switch_layer(1)
    qtbot.waitUntil(lambda: hl.animation.state() == QAbstractAnimation.Stopped, timeout=2000)
    r = hl.indicator_rect()
    b = buttons[1]
    top_left = b.mapTo(hl.parentWidget(), b.rect().topLeft())
    assert abs(hl.mapTo(hl.parentWidget(), r.topLeft().toPoint()).y() - top_left.y()) <= 1
    assert abs(r.height() - b.height()) <= 1 and abs(r.width() - b.width()) <= 1


def test_layer_button_stylesheet(qtbot):
    import branding_theme
    import themes
    branding_theme.register()
    themes.Theme.set_theme("KeRT Light")
    from PyQt5.QtWidgets import QApplication
    css = QApplication.instance().styleSheet()
    import re
    block = re.search(r'QPushButton\[layerButton="true"\][^{]*\{([^}]*)\}', css)
    assert block, "layer button rule"
    assert "background-color: transparent" in block.group(1)
    lit_colour = QApplication.palette().color(QPalette.HighlightedText).name()
    assert '[lit="true"]' in css and "color: " + lit_colour in css.split('[lit="true"]')[1].split("}")[0]


# ---------------------------------------------------------------- tab fade

def test_tab_click_fades(qtbot):
    from widgets import tab_fade

    mw = prepared(qtbot)
    tabs = mw.tabs
    assert tab_fade.FADE_OUT_MS + tab_fade.FADE_IN_MS == 300
    bar = tabs.tabBar()
    qtbot.waitUntil(lambda: bar.isVisible() and bar.count() >= 2)
    stack = tabs.findChild(QStackedWidget)
    f = tab_fade.fader(tabs)
    target = 1
    # record the state at the start of each phase (polling could miss a 150 ms phase on a busy machine)
    seen = []
    original_run = f.run

    def recording_run(phase, start, end, ms):
        seen.append((phase, tabs.currentIndex(), f.overlay.snapshot is not None, f.overlay.isVisible(), ms))
        original_run(phase, start, end, ms)
    f.run = recording_run

    qtbot.mouseClick(bar, Qt.LeftButton, pos=bar.tabRect(target).center())
    # fading out first: still the old page, covered by the fading overlay (a snapshot of it)
    assert tabs.currentIndex() == 0
    assert f.busy() and f.overlay.isVisible() and f.overlay.snapshot is not None
    assert f.overlay.geometry() == stack.geometry()
    # the overlay paints every pixel itself, so nothing under it is repainted on each frame
    assert f.overlay.testAttribute(Qt.WA_OpaquePaintEvent)
    qtbot.waitUntil(lambda: not f.busy() and not f.overlay.isVisible(), timeout=3000)   # faded in, overlay gone
    assert tabs.currentIndex() == target
    # out on the old page, then in on the new one from a picture of it (not the live page)
    assert seen == [("out", 0, True, True, tab_fade.FADE_OUT_MS), ("in", target, True, True, tab_fade.FADE_IN_MS)]
    assert stack.graphicsEffect() is None      # the pages themselves are never re-rendered through an effect


def test_programmatic_switch_is_immediate(qtbot):
    mw = prepared(qtbot)
    from widgets import tab_fade
    mw.tabs.setCurrentIndex(1)
    assert mw.tabs.currentIndex() == 1
    assert not tab_fade.fader(mw.tabs).busy()


def test_every_tab_widget_fades(qtbot):
    from widgets import tab_fade

    mw = prepared(qtbot)
    widgets = mw.findChildren(QTabWidget) + mw.tray_keycodes.findChildren(QTabWidget)
    assert len(widgets) >= 4
    assert all(tab_fade.is_enabled(w) for w in widgets), [type(w).__name__ for w in widgets if not tab_fade.is_enabled(w)]


def test_lit_labels_correct_after_first_layout(qtbot):
    """At start-up the highlight gets its buttons before they are laid out (all at the default
    geometry, on top of each other); once the layout places them, only layer 0's label may be white"""
    from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QWidget
    from widgets.layer_highlight import LayerHighlight

    parent = QWidget()
    qtbot.addWidget(parent)
    column = QVBoxLayout(parent)
    hl = LayerHighlight(parent)
    buttons = []
    for i in range(4):
        b = QPushButton(str(i))
        b.setProperty("layerButton", True)
        column.addWidget(b)
        buttons.append(b)
    hl.set_buttons(buttons)                # not shown, not laid out yet
    parent.resize(200, 300)
    parent.show()
    qtbot.waitUntil(lambda: buttons[3].y() > buttons[0].y() + 3 * buttons[0].height() // 2 and hl.isVisible())
    qtbot.waitUntil(lambda: [b.property("lit") for b in buttons] == [True, False, False, False], timeout=1000)


def test_web_fade_uses_the_page_overlay(qtbot, monkeypatch):
    """Browser build: Qt draws in software there (a full-page crossfade managed 3 frames in 0.35 s), so
    the fade is handed to the page (a CSS-animated box over the page area): Python asks for "out",
    switches the tab under the covered area after FADE_OUT_MS, then asks for "in"."""
    import types
    from widgets import tab_fade

    calls = []
    monkeypatch.setitem(sys.modules, "vialglue", types.SimpleNamespace(fade=lambda *a: calls.append(a)))
    monkeypatch.setattr(tab_fade, "WEB", True)
    mw = prepared(qtbot)
    settled(qtbot, mw.keymap_editor)
    tabs = mw.tabs
    f = tab_fade.fader(tabs)
    bar = tabs.tabBar()
    stack = tabs.findChild(QStackedWidget)
    qtbot.mouseClick(bar, Qt.LeftButton, pos=bar.tabRect(1).center())

    assert tabs.currentIndex() == 0 and f.busy()
    assert not f.overlay.isVisible(), "no Qt-drawn overlay in the browser"
    assert calls and calls[0][0] == "out"
    top_left = stack.mapToGlobal(stack.rect().topLeft())
    assert calls[0][1:] == (top_left.x(), top_left.y(), stack.width(), stack.height(), tab_fade.FADE_OUT_MS)
    qtbot.waitUntil(lambda: tabs.currentIndex() == 1, timeout=1500)
    qtbot.waitUntil(lambda: any(c[0] == "in" for c in calls), timeout=1500)
    assert [c for c in calls if c[0] == "in"][0][-1] == tab_fade.FADE_IN_MS
    qtbot.waitUntil(lambda: not f.busy(), timeout=1500)
