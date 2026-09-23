# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTabWidget, QWidget, QScrollArea, QApplication, QVBoxLayout, QHBoxLayout, QSizePolicy, \
    QWIDGETSIZE_MAX
from PyQt5.QtGui import QPalette

from constants import KEYCODE_BTN_RATIO, PICKER_FONT_DELTA
import key_style
from widgets.display_keyboard import DisplayKeyboard
from widgets.display_keyboard_defs import ansi_100, ansi_80, ansi_70, iso_100, iso_80, iso_70, mods, mods_narrow
from widgets.flowlayout import FlowLayout
from keycodes.keycodes import KEYCODES_BASIC, KEYCODES_ISO, KEYCODES_MACRO, KEYCODES_LAYERS, KEYCODES_QUANTUM, \
    KEYCODES_BOOT, KEYCODES_MODIFIERS, \
    KEYCODES_BACKLIGHT, KEYCODES_MEDIA, KEYCODES_SPECIAL, KEYCODES_SHIFTED, KEYCODES_USER, Keycode, \
    KEYCODES_TAP_DANCE, KEYCODES_HOST_OS, KEYCODES_MIDI, KEYCODES_BASIC_NUMPAD, KEYCODES_BASIC_NAV, KEYCODES_ISO_KR
from widgets.square_button import SquareButton
from widgets.entry_card_button import EntryCardButton
from util import tr, KeycodeDisplay


class AlternativeDisplay(QWidget):

    keycode_changed = pyqtSignal(str)

    def __init__(self, kbdef, keycodes, prefix_buttons):
        super().__init__()

        self.kb_display = None
        self.keycodes = keycodes
        self.buttons = []

        self.key_layout = FlowLayout()

        if prefix_buttons:
            for title, code in prefix_buttons:
                btn = SquareButton()
                btn.setFontDelta(PICKER_FONT_DELTA)
                btn.setRelSize(KEYCODE_BTN_RATIO)
                btn.setText(title)
                btn.clicked.connect(lambda st, k=code: self.keycode_changed.emit(title))
                self.key_layout.addWidget(btn)

        # everything is left-aligned inside one block; the block is as wide as the display keyboard
        # (full width when there is none) and centred in the tab page
        block_layout = QVBoxLayout()
        block_layout.setContentsMargins(0, 0, 0, 0)
        if kbdef:
            self.kb_display = DisplayKeyboard(kbdef)
            self.kb_display.keycode_changed.connect(self.keycode_changed)
            block_layout.addWidget(self.kb_display)
            block_layout.setAlignment(self.kb_display, Qt.AlignLeft)
        block_layout.addLayout(self.key_layout)
        self.block = QWidget()
        self.block.setLayout(block_layout)

        # the block is centred with stretches; its width is fixed in update_block_width()
        self.wrap_width = None
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(self.block)
        row.addStretch(1)
        self.row = row
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addStretch(1)
        self.setLayout(layout)

    def button_gap(self, w):
        """Horizontal distance FlowLayout puts between two buttons"""
        return self.key_layout.spacing() + w.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton,
                                                                   Qt.Horizontal)

    def flow_row_width(self):
        """Width the flow layout would need to put every button on one row, at the buttons' natural
        widths (w.sizeHint(): not clamped by a width set in fit_card_buttons)"""
        width = 0
        for i in range(self.key_layout.count()):
            item = self.key_layout.itemAt(i)
            w = item.widget()
            if w is None or w.isHidden():
                continue
            width += w.sizeHint().width() + self.button_gap(w)
        return width

    def card_buttons(self):
        return [b for b in self.buttons if isinstance(b, EntryCardButton) and not b.isHidden()]

    def fit_card_buttons(self, block_width, wrapping):
        """Tap Dance / HostOS / Macro cards: when they wrap, widen them equally so that every full row
        spans the block (as the editors' cards do); otherwise they keep their natural width"""
        cards = self.card_buttons()
        if not cards:
            return
        if not wrapping:
            for b in cards:
                if b.maximumWidth() != QWIDGETSIZE_MAX:
                    b.setMinimumWidth(0)
                    b.setMaximumWidth(QWIDGETSIZE_MAX)
            return
        # FlowLayout keeps a button on the row while its right edge is <= rect.right()
        gap = self.button_gap(cards[0])
        row = block_width - 1
        side = max(b.sizeHint().width() for b in cards)
        n = max(1, (row + gap) // (side + gap))
        width = max(side, (row - (n - 1) * gap) // n)
        for b in cards:
            if b.maximumWidth() != width or b.minimumWidth() != width:
                b.setFixedWidth(width)
        self.key_layout.invalidate()

    def available_width(self):
        """Width of the enclosing scroll area's viewport (the tab page). Our own width is not usable
        here: it follows the block width we set (through the scroll area's content minimum), so
        basing the block on it makes two displays in one tab resize each other forever."""
        w = self.parentWidget()
        while w is not None and not isinstance(w, QScrollArea):
            w = w.parentWidget()
        width = w.viewport().width() if w is not None else self.width()
        if self.wrap_width:
            width = min(width, self.wrap_width)
        return width

    def set_wrap_width(self, wrap_width):
        """Limit the (centred, left-aligned inside) block to wrap_width pixels; None = full width"""
        self.wrap_width = wrap_width
        self.update_block_width()

    def update_block_width(self):
        """The block is as wide as its contents want (the display keyboard, or one row of buttons),
        capped at the available width: the wrap width (window height in landscape windows) or the
        page width. So a keyboard tab's buttons wrap at the wrap width, not at the (possibly narrow)
        display keyboard. Either way the block is centred and its contents are left-aligned."""
        natural = max(self.flow_row_width(), 1)
        if self.kb_display:
            natural = max(natural, self.kb_display.sizeHint().width())
        available = self.available_width()
        width = min(available, natural)
        if not self.kb_display:
            self.fit_card_buttons(width, natural > available)
        if width > 0 and self.block.width() != width:
            self.block.setFixedWidth(width)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.update_block_width()

    def recreate_buttons(self, keycode_filter):
        for btn in self.buttons:
            # take it out of the flow layout too, otherwise the dead item keeps adding spacing
            self.key_layout.removeWidget(btn)
            btn.hide()
            btn.deleteLater()
        self.buttons = []

        for keycode in self.keycodes:
            if keycode.hidden or not keycode_filter(keycode.qmk_id):
                continue
            # Tap Dance / HostOS entries get a card showing their contents (see entry_labels.py)
            btn = EntryCardButton() if hasattr(keycode, "summary") else SquareButton()
            btn.frame_extra = key_style.OUTLINE_WIDTH
            btn.setFontDelta(PICKER_FONT_DELTA)
            btn.setRelSize(KEYCODE_BTN_RATIO)
            btn.setToolTip(Keycode.tooltip(keycode.qmk_id))
            btn.clicked.connect(lambda st, k=keycode: self.keycode_changed.emit(k.qmk_id))
            btn.keycode = keycode
            self.key_layout.addWidget(btn)
            self.buttons.append(btn)

        self.relabel_buttons()
        self.update_block_width()

    def relabel_buttons(self):
        if self.kb_display:
            self.kb_display.relabel_buttons()

        KeycodeDisplay.relabel_buttons(self.buttons)

    def required_width(self):
        return self.kb_display.sizeHint().width() if self.kb_display else 0

    def has_buttons(self):
        return len(self.buttons) > 0


class Tab(QScrollArea):

    keycode_changed = pyqtSignal(str)

    def __init__(self, parent, label, alts, prefix_buttons=None):
        super().__init__(parent)

        self.label = label
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        # The alternative displays (display keyboard + keycode buttons) are built on first show only:
        # a MainWindow has four pickers x eleven tabs of them, and building all of that up front took
        # most of the startup time (docs/picker-lazy-build-spec.md).
        self.alts = alts
        self.prefix_buttons = prefix_buttons
        self.alternatives = []
        self.keycode_filter = keycode_filter_any
        self.wrap_width = None
        self.built = False
        self.dirty = True
        self.suspended = False    # set while the tab widget shuffles pages around (see recreate_keycode_buttons)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)

        w = QWidget()
        w.setLayout(self.layout)
        self.setWidget(w)

    def would_have_buttons(self, keycode_filter):
        """Whether any keycode of this tab passes the filter: decides the tab's presence without widgets"""
        return any(not kc.hidden and keycode_filter(kc.qmk_id) for _, keycodes in self.alts for kc in keycodes)

    def invalidate(self, keycode_filter):
        """Remember the filter and rebuild now if the tab is on screen, otherwise on the next show"""
        self.keycode_filter = keycode_filter
        self.dirty = True
        if self.isVisible():
            self.ensure_built()

    def ensure_built(self):
        if not self.dirty or self.suspended:
            return
        if not self.alternatives:
            for kb, keys in self.alts:
                alt = AlternativeDisplay(kb, keys, self.prefix_buttons)
                alt.keycode_changed.connect(self.keycode_changed)
                alt.set_wrap_width(self.wrap_width)
                self.layout.addWidget(alt)
                self.alternatives.append(alt)
        for alt in self.alternatives:
            alt.recreate_buttons(self.keycode_filter)
        self.built = True
        self.dirty = False
        self.select_alternative()

    def showEvent(self, ev):
        super().showEvent(ev)
        self.ensure_built()

    def set_wrap_width(self, wrap_width):
        self.wrap_width = wrap_width
        for alt in self.alternatives:
            alt.set_wrap_width(wrap_width)
        self.select_alternative()

    def recreate_buttons(self, keycode_filter):
        self.invalidate(keycode_filter)

    def relabel_buttons(self):
        for alt in self.alternatives:
            alt.relabel_buttons()

    def has_buttons(self):
        for alt in self.alternatives:
            if alt.has_buttons():
                return True
        return False

    def select_alternative(self):
        # hide everything first
        for alt in self.alternatives:
            alt.hide()

        # then display first alternative which fits on screen w/o horizontal scroll
        available = self.width() - self.verticalScrollBar().width()
        if self.wrap_width:
            available = min(available, self.wrap_width)
        for alt in self.alternatives:
            if available > alt.required_width():
                alt.show()
                break

    def resizeEvent(self, evt):
        super().resizeEvent(evt)
        self.select_alternative()


class SimpleTab(Tab):

    def __init__(self, parent, label, keycodes):
        super().__init__(parent, label, [(None, keycodes)])


def keycode_filter_any(kc):
    return True


def keycode_filter_masked(kc):
    return Keycode.is_basic(kc)


class FilteredTabbedKeycodes(QTabWidget):

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self, parent=None, keycode_filter=keycode_filter_any):
        super().__init__(parent)

        self.keycode_filter = keycode_filter
        self.setObjectName("picker_tabs")   # the stylesheet centres this tab bar

        self.tabs = [
            Tab(self, "Basic", [
                (ansi_100, KEYCODES_SPECIAL + KEYCODES_SHIFTED),
                (ansi_80, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_SHIFTED),
                (ansi_70, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_BASIC_NAV + KEYCODES_SHIFTED),
                (None, KEYCODES_SPECIAL + KEYCODES_BASIC + KEYCODES_SHIFTED),
            ], prefix_buttons=[("Any", -1)]),
            Tab(self, "ISO/JIS", [
                (iso_100, KEYCODES_SPECIAL + KEYCODES_SHIFTED + KEYCODES_ISO_KR),
                (iso_80, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_SHIFTED + KEYCODES_ISO_KR),
                (iso_70, KEYCODES_SPECIAL + KEYCODES_BASIC_NUMPAD + KEYCODES_BASIC_NAV + KEYCODES_SHIFTED +
                 KEYCODES_ISO_KR),
                (None, KEYCODES_ISO),
            ], prefix_buttons=[("Any", -1)]),
            SimpleTab(self, "Layers", KEYCODES_LAYERS),
            Tab(self, "Quantum", [(mods, (KEYCODES_BOOT + KEYCODES_QUANTUM)),
                                  (mods_narrow, (KEYCODES_BOOT + KEYCODES_QUANTUM)),
                                  (None, (KEYCODES_BOOT + KEYCODES_MODIFIERS + KEYCODES_QUANTUM))]),
            SimpleTab(self, "Backlight", KEYCODES_BACKLIGHT),
            SimpleTab(self, "App, Media and Mouse", KEYCODES_MEDIA),
            SimpleTab(self, "MIDI", KEYCODES_MIDI),
            SimpleTab(self, "Tap Dance", KEYCODES_TAP_DANCE),
            SimpleTab(self, "HostOS", KEYCODES_HOST_OS),
            SimpleTab(self, "User", KEYCODES_USER),
            SimpleTab(self, "Macro", KEYCODES_MACRO),
        ]

        for tab in self.tabs:
            tab.keycode_changed.connect(self.on_keycode_changed)

        self.recreate_keycode_buttons()
        KeycodeDisplay.notify_keymap_override(self)

    def on_keycode_changed(self, code):
        if code == "Any":
            self.anykey.emit()
        else:
            self.keycode_changed.emit(Keycode.normalize(code))

    def recreate_keycode_buttons(self):
        prev_tab = self.tabText(self.currentIndex()) if self.currentIndex() >= 0 else ""
        # removing / adding pages makes each of them "current" (and shown) for a moment; no page may
        # build itself during that shuffle, only the one that ends up current
        for tab in self.tabs:
            tab.suspended = True
        while self.count() > 0:
            self.removeTab(0)

        for tab in self.tabs:
            tab.invalidate(self.keycode_filter)
            if tab.would_have_buttons(self.keycode_filter):
                self.addTab(tab, tr("TabbedKeycodes", tab.label))
                if tab.label == prev_tab:
                    self.setCurrentIndex(self.count() - 1)
            else:
                tab.hide()
        for tab in self.tabs:
            tab.suspended = False
        if self.isVisible() and self.currentWidget() is not None:
            self.currentWidget().ensure_built()

    def on_keymap_override(self):
        for tab in self.tabs:
            tab.relabel_buttons()

    def set_wrap_width(self, wrap_width):
        for tab in self.tabs:
            tab.set_wrap_width(wrap_width)


class TabbedKeycodes(QWidget):

    keycode_changed = pyqtSignal(str)
    anykey = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.target = None
        self.is_tray = False
        self.wrap_width = None

        self.layout = QVBoxLayout()

        self.all_keycodes = FilteredTabbedKeycodes()
        self.basic_keycodes = FilteredTabbedKeycodes(keycode_filter=keycode_filter_masked)
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.keycode_changed.connect(self.keycode_changed)
            opt.anykey.connect(self.anykey)
            self.layout.addWidget(opt)

        self.setLayout(self.layout)
        self.set_keycode_filter(keycode_filter_any)

    def hasHeightForWidth(self):
        # The flow layouts inside (thousands of keycode buttons) would be laid out again in Python for every
        # height-for-width query of the enclosing layouts / splitter, which stalls the UI for seconds.
        # The picker's height is decided by the Keymap splitter, not by its content.
        return False

    @classmethod
    def set_tray(cls, tray):
        cls.tray = tray

    @classmethod
    def open_tray(cls, target, keycode_filter=None):
        cls.tray.set_keycode_filter(keycode_filter)
        cls.tray.show()
        if cls.tray.target is not None and cls.tray.target != target:
            cls.tray.target.deselect()
        cls.tray.target = target

    @classmethod
    def close_tray(cls):
        if cls.tray.target is not None:
            cls.tray.target.deselect()
        cls.tray.target = None
        cls.tray.hide()

    def make_tray(self):
        self.is_tray = True
        TabbedKeycodes.set_tray(self)

        self.keycode_changed.connect(self.on_tray_keycode_changed)
        self.anykey.connect(self.on_tray_anykey)

    def on_tray_keycode_changed(self, kc):
        if self.target is not None:
            self.target.on_keycode_changed(kc)

    def on_tray_anykey(self):
        if self.target is not None:
            self.target.on_anykey()

    def recreate_keycode_buttons(self):
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.recreate_keycode_buttons()

    def set_wrap_width(self, wrap_width):
        """Wrap the pickers' contents at wrap_width pixels (None: full width); the block stays centred"""
        self.wrap_width = wrap_width
        for opt in [self.all_keycodes, self.basic_keycodes]:
            opt.set_wrap_width(wrap_width)

    def set_keycode_filter(self, keycode_filter):
        if keycode_filter == keycode_filter_masked:
            self.all_keycodes.hide()
            self.basic_keycodes.show()
        else:
            self.all_keycodes.show()
            self.basic_keycodes.hide()
