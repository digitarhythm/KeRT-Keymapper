# SPDX-License-Identifier: GPL-2.0-or-later
"""Key look trial (2026-09-29, docs/dark-keys-spec.md): keys are a black face with a white legend, no
outline, 8 px corners and a soft black drop shadow, both on the keymap and in the pickers.
key_style.DARK_KEYS = False brings back the white face with a 3 px outline."""
import os
import sys

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(__file__))


def contrast(a, b):
    def lum(c):
        def ch(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * ch(c.red()) + 0.7152 * ch(c.green()) + 0.0722 * ch(c.blue())
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def themed():
    import branding_theme
    import themes
    branding_theme.register()
    themes.Theme.set_theme("KeRT Light")


def test_constants():
    import key_style
    assert key_style.DARK_KEYS is True
    assert QColor(key_style.KEY_FACE) == QColor("#000000")
    assert QColor(key_style.KEY_LEGEND) == QColor("#ffffff")
    assert key_style.KEY_RADIUS == 8
    assert key_style.key_corner() == 8
    # a remapped legend (Colemak etc.) must read on black: not the dark Link blue
    assert contrast(key_style.override_color(), QColor(key_style.KEY_FACE)) >= 4.5
    assert contrast(QColor(key_style.KEY_MASK_FACE), QColor(key_style.KEY_LEGEND)) >= 4.5


def keywidget(qtbot):
    from widgets.key_widget import KeyWidget
    themed()
    w = KeyWidget()
    w.set_keycode("KC_A")
    qtbot.addWidget(w)
    w.resize(w.minimumSizeHint())
    return w


def test_keymap_key_is_black_with_white_legend_and_shadow(qtbot):
    import key_style
    w = keywidget(qtbot)
    key = w.widgets[0]
    assert key.corner == key_style.KEY_RADIUS
    img = w.grab().toImage()
    r = key.rect
    inner = QColor(img.pixel(r.left() + r.width() // 4, r.top() + r.height() // 4))
    assert inner == QColor(key_style.KEY_FACE)
    legend = [QColor(img.pixel(x, y)) for x in range(r.center().x() - 8, r.center().x() + 8)
              for y in range(r.center().y() - 8, r.center().y() + 8)]
    assert any(c == QColor(key_style.KEY_LEGEND) for c in legend), "white legend"
    # key.rect is in key coordinates; on screen the key sits at (shift_x, shift_y)
    x = int(key.shift_x) + r.center().x()
    top = int(key.shift_y) + r.top()
    bottom = int(key.shift_y) + r.bottom()
    # no outline: the face colour runs right up to the edge (no lighter or darker ring inside it)
    edge = [QColor(img.pixel(x, y)) for y in range(top + 1, top + 5)]
    assert all(c == QColor(key_style.KEY_FACE) for c in edge)
    # the widget leaves room for the shadow below the key
    assert img.height() - 1 - bottom >= key_style.SHADOW_OFFSET + key_style.SHADOW_BLUR - 1
    # a soft shadow below the key: darker than the window background, lighter further down
    bg = QApplication.palette().color(QPalette.Window)
    shade = [QColor(img.pixel(x, y)).lightness() for y in range(bottom + 2, bottom + 2 + key_style.SHADOW_BLUR)]
    assert shade[0] < bg.lightness() - 20 and shade[0] > 0
    assert shade == sorted(shade) and shade[-1] > shade[0], shade


def test_selected_key_is_highlight_grey(qtbot):
    w = keywidget(qtbot)
    key = w.widgets[0]
    w.active_key = key
    img = w.grab().toImage()
    r = key.rect
    pal = QApplication.palette()
    assert QColor(img.pixel(r.left() + r.width() // 4, r.top() + r.height() // 4)) == pal.color(QPalette.Highlight)
    legend = [QColor(img.pixel(x, y)) for x in range(r.center().x() - 8, r.center().x() + 8)
              for y in range(r.center().y() - 8, r.center().y() + 8)]
    assert any(c == pal.color(QPalette.HighlightedText) for c in legend)


def test_picker_key_buttons(qtbot):
    import re
    import key_style
    from test_gui import prepare, FAKE_KEYBOARD
    from widgets.square_button import SquareButton
    from widgets.entry_card_button import EntryCardButton

    themed()
    css = QApplication.instance().styleSheet()
    block = re.search(r'QPushButton\[keyButton="true"\]\s*\{([^}]*)\}', css)
    assert block
    b = block.group(1)
    assert "background-color: %s" % key_style.KEY_FACE in b and "color: %s" % key_style.KEY_LEGEND in b
    assert "border: none" in b and "border-radius: %dpx" % key_style.KEY_RADIUS in b and "margin:" in b

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    qtbot.waitUntil(lambda: any(isinstance(x, SquareButton) and x.isVisible() and x.property("keyButton")
                                for x in ak.currentWidget().findChildren(SquareButton)))
    keys = [x for x in ak.currentWidget().findChildren(SquareButton) if x.isVisible()]
    assert all(x.property("keyButton") for x in keys if not isinstance(x, EntryCardButton))
    btn = next(x for x in keys if x.property("keyButton") and x.text == "A")    # SquareButton keeps .text as a str
    # grab it inside the window: grabbing the button alone fills its margins with the stylesheet's
    # background colour, while on screen the page shows through them (with the shadow on top)
    win = btn.window()
    tl = btn.mapTo(win, btn.rect().topLeft())
    img = win.grab().toImage().copy(tl.x(), tl.y(), btn.width(), btn.height())
    ml, mt, mr, mb = key_style.KEY_MARGINS
    # the face: black, well inside the margins and away from the legend
    assert QColor(img.pixel(ml + 3, mt + 3)) == QColor(key_style.KEY_FACE)
    # the shadow in the bottom margin, under the middle of the key
    x = img.width() // 2
    assert QColor(img.pixel(x, img.height() - mb - 1)) == QColor(key_style.KEY_FACE)     # last row of the face
    shade = [QColor(img.pixel(x, y)).lightness() for y in range(img.height() - mb, img.height())]
    # a shadow that fades out downwards (the first row mixes with the face's antialiased edge)
    darkest = shade.index(min(shade))
    assert 0 < min(shade) < 150 and darkest <= 1, shade
    assert shade[darkest:] == sorted(shade[darkest:]) and shade[-1] > min(shade) + 60, shade


def test_off_switch_restores_the_outlined_look(qtbot, monkeypatch):
    import key_style
    monkeypatch.setattr(key_style, "DARK_KEYS", False)
    assert key_style.key_corner() == key_style.CORNER_RADIUS
    w = keywidget(qtbot)
    img = w.grab().toImage()
    r = w.widgets[0].rect
    assert QColor(img.pixel(r.left() + r.width() // 4, r.top() + r.height() // 4)) == QApplication.palette().color(QPalette.Button)


# ---- tabs and layer buttons look like keys too (2026-09-30)

def window(qtbot):
    from test_ui_motion import prepared, settled
    themed()
    mw = prepared(qtbot)
    settled(qtbot, mw.keymap_editor)
    return mw


def shot(widget):
    """widget as it looks on screen: cut out of a grab of its window (a lone grab paints its margins
    with the stylesheet background)"""
    win = widget.window()
    tl = widget.mapTo(win, widget.rect().topLeft())
    return win.grab().toImage().copy(tl.x(), tl.y(), widget.width(), widget.height())


def test_tab_style(qtbot):
    import re
    import key_style
    themed()
    css = QApplication.instance().styleSheet()
    tabs = re.findall(r'QTabBar::tab\s*\{([^}]*)\}', css)
    last = tabs[-1]           # the dark key rules come last and win
    assert "background-color: %s" % key_style.KEY_FACE in last and "color: %s" % key_style.KEY_LEGEND in last
    assert "border: none" in last and "border-radius: %dpx" % key_style.KEY_RADIUS in last and "margin:" in last
    sel = re.findall(r'QTabBar::tab:selected\s*\{([^}]*)\}', css)[-1]
    pal = QApplication.palette()
    assert "background-color: %s" % pal.color(QPalette.Highlight).name() in sel
    assert "color: %s" % pal.color(QPalette.HighlightedText).name() in sel


def test_tabs_black_with_shadow(qtbot):
    import key_style
    mw = window(qtbot)
    bar = mw.tabs.tabBar()
    assert bar.property("keyShadow")
    img = shot(bar)
    r = bar.tabRect(1)                      # not selected
    ml, mt, mr, mb = key_style.KEY_MARGINS
    face = QColor(img.pixel(r.left() + ml + 3, r.top() + mt + 3))
    assert face == QColor(key_style.KEY_FACE)
    x = r.center().x()
    shade = [QColor(img.pixel(x, y)).lightness() for y in range(r.bottom() - mb + 1, r.bottom() + 1)]
    assert 0 < min(shade) < 150 and shade[-1] > min(shade) + 40, shade
    sel = bar.tabRect(0)
    assert QColor(img.pixel(sel.left() + ml + 3, sel.top() + mt + 3)) == QApplication.palette().color(QPalette.Highlight)


def test_layer_buttons_black_with_shadow(qtbot):
    import key_style
    mw = window(qtbot)
    ke = mw.keymap_editor
    hl = ke.layer_highlight
    buttons = ke.layer_buttons[:ke.keyboard.layers]
    parent = hl.parentWidget()
    img = shot(parent)
    pal = QApplication.palette()

    def at(btn, dx, dy):
        p = btn.mapTo(parent, btn.rect().topLeft())
        return QColor(img.pixel(p.x() + dx, p.y() + dy))
    assert at(buttons[1], 4, 4) == QColor(key_style.KEY_FACE)           # another layer: black face
    assert at(buttons[0], 4, 4) == pal.color(QPalette.Highlight)       # the current layer: highlight
    # its label is dark on the light highlight (the current layer's button is disabled: that state must
    # not bring back the white legend)
    b0 = buttons[0]
    label = [at(b0, x, y).lightness() for x in range(b0.width() // 2 - 6, b0.width() // 2 + 6)
             for y in range(b0.height() // 2 - 6, b0.height() // 2 + 6)]
    assert min(label) < 100, "dark label on the current layer"
    # no outline: the face runs right up to the edge
    assert at(buttons[1], buttons[1].width() // 2, 1) == QColor(key_style.KEY_FACE)
    # a shadow under the last button, inside the highlight's area (it covers the shadow margins too)
    last = buttons[-1]
    below = [at(last, last.width() // 2, last.height() + k).lightness() for k in range(0, 5)]
    assert 0 < min(below) < 150 and below[-1] > min(below), below
    # white labels on both the black and the grey faces
    import re
    css = QApplication.instance().styleSheet()
    blocks = re.findall(r'QPushButton\[layerButton="true"\][^{]*\{([^}]*)\}', css)
    block = [b for b in blocks if "border: none" in b][-1]
    assert "color: %s" % key_style.KEY_LEGEND in block



# ---- the keyboard selector and the zoom buttons look like keys too (2026-09-30)

def test_selector_looks_like_a_key(qtbot):
    import re
    import key_style
    mw = window(qtbot)
    cb = mw.combobox_devices
    css = QApplication.instance().styleSheet()
    block = re.findall(r'DeviceComboBox\s*\{([^}]*)\}', css)
    assert block, "selector rule"
    b = block[-1]
    assert "background-color: %s" % key_style.KEY_FACE in b and "border: none" in b
    assert "border-radius: %dpx" % key_style.KEY_RADIUS in b and "margin:" in b
    img = shot(cb)
    ml, mt, mr, mb = key_style.KEY_MARGINS
    assert QColor(img.pixel(ml + 3, cb.height() // 2)) == QColor(key_style.KEY_FACE)      # left of the text
    text = cb.text_area()
    names = [QColor(img.pixel(x, y)) for x in range(text.left(), min(text.right(), text.left() + 120))
             for y in range(text.top(), text.bottom())]
    assert any(c.lightness() > 230 for c in names), "white keyboard name"
    x = cb.width() // 2
    shade = [QColor(img.pixel(x, y)).lightness() for y in range(cb.height() - mb, cb.height())]
    assert 0 < min(shade) < 150 and shade[-1] > min(shade) + 40, shade


def test_zoom_buttons_look_like_keys(qtbot):
    import key_style
    mw = window(qtbot)
    ke = mw.keymap_editor
    zoom = ke.layer_buttons[ke.keyboard.layers:]
    assert len(zoom) == 2 and all(b.property("keyButton") for b in zoom)
    assert all(b.frame_extra == key_style.OUTLINE_WIDTH for b in zoom), "room for the margins"
    img = shot(zoom[0])
    ml, mt, mr, mb = key_style.KEY_MARGINS
    # left edge, half way down: inside the face, clear of the rounded corners and of the +/- sign
    assert QColor(img.pixel(ml + 2, img.height() // 2)) == QColor(key_style.KEY_FACE)
