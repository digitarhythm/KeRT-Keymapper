# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QSizePolicy, QGridLayout, QVBoxLayout, QLabel, QHBoxLayout, \
    QPushButton, QSpinBox

from protocol.constants import VIAL_PROTOCOL_DYNAMIC
from widgets.key_widget import KeyWidget
from util import tr
from vial_device import VialKeyboard
from editor.basic_editor import BasicEditor
from widgets.entry_card import EntryCard, EntryCardContainer
import entry_labels

# キーの描画倍率。カード内では通常より小さく描いて行間を詰める
CARD_KEY_SCALE = 0.7


class TapDanceEntryUI(QObject):

    key_changed = pyqtSignal()
    timing_changed = pyqtSignal()

    def __init__(self, idx):
        super().__init__()

        self.idx = idx
        self.container = QGridLayout()
        self.populate_container()

        w = QWidget()
        w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        w.setLayout(self.container)
        l = QVBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(w)
        l.setAlignment(w, QtCore.Qt.AlignHCenter)
        self.w2 = QWidget()
        self.w2.setLayout(l)

    def populate_container(self):
        self.container.setVerticalSpacing(3)
        self.container.addWidget(QLabel(tr("TapDance", "On tap")), 0, 0)
        self.kc_on_tap = KeyWidget()
        self.kc_on_tap.changed.connect(self.on_key_changed)
        self.container.addWidget(self.kc_on_tap, 0, 1)
        self.container.addWidget(QLabel(tr("TapDance", "On hold")), 1, 0)
        self.kc_on_hold = KeyWidget()
        self.kc_on_hold.changed.connect(self.on_key_changed)
        self.container.addWidget(self.kc_on_hold, 1, 1)
        self.container.addWidget(QLabel(tr("TapDance", "On double tap")), 2, 0)
        self.kc_on_double_tap = KeyWidget()
        self.kc_on_double_tap.changed.connect(self.on_key_changed)
        self.container.addWidget(self.kc_on_double_tap, 2, 1)
        self.container.addWidget(QLabel(tr("TapDance", "On tap + hold")), 3, 0)
        self.kc_on_tap_hold = KeyWidget()
        self.kc_on_tap_hold.changed.connect(self.on_key_changed)
        self.container.addWidget(self.kc_on_tap_hold, 3, 1)
        self.container.addWidget(QLabel(tr("TapDance", "Tapping term (ms)")), 4, 0)
        self.txt_tapping_term = QSpinBox()
        self.txt_tapping_term.valueChanged.connect(self.on_timing_changed)
        self.txt_tapping_term.setMinimum(0)
        self.txt_tapping_term.setMaximum(10000)
        self.container.addWidget(self.txt_tapping_term, 4, 1)
        for kc in (self.kc_on_tap, self.kc_on_hold, self.kc_on_double_tap, self.kc_on_tap_hold):
            kc.set_scale(CARD_KEY_SCALE)

    def widget(self):
        return self.w2

    def load(self, data):
        objs = [self.kc_on_tap, self.kc_on_hold, self.kc_on_double_tap, self.kc_on_tap_hold, self.txt_tapping_term]
        for o in objs:
            o.blockSignals(True)

        self.kc_on_tap.set_keycode(data[0])
        self.kc_on_hold.set_keycode(data[1])
        self.kc_on_double_tap.set_keycode(data[2])
        self.kc_on_tap_hold.set_keycode(data[3])
        self.txt_tapping_term.setValue(data[4])

        for o in objs:
            o.blockSignals(False)

    def save(self):
        return (
            self.kc_on_tap.keycode,
            self.kc_on_hold.keycode,
            self.kc_on_double_tap.keycode,
            self.kc_on_tap_hold.keycode,
            self.txt_tapping_term.value()
        )

    def on_key_changed(self):
        self.key_changed.emit()

    def on_timing_changed(self):
        self.timing_changed.emit()


class TapDance(BasicEditor):

    def __init__(self):
        super().__init__()
        self.keyboard = None

        self.tap_dance_entries = []
        self.tap_dance_entries_available = []
        self.cards_available = []
        self.cards = []
        self.container = EntryCardContainer()
        # entries are created on demand (ensure_entries), as many as the keyboard has

        self.hint = QLabel(tr("TapDance", "Use <code>TD(n)</code> to set up these actions in the keymap."))
        self.addWidget(self.hint)
        self.addWidget(self.container)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_save = QPushButton(tr("TapDance", "Save"))
        self.btn_save.clicked.connect(self.on_save)
        self.btn_revert = QPushButton(tr("TapDance", "Revert"))
        self.btn_revert.clicked.connect(self.on_revert)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_revert)
        self.addLayout(buttons)

    def ensure_entries(self, count):
        """Create entry widgets (and their cards) until `count` exist; at most 128."""
        while len(self.tap_dance_entries_available) < min(count, 128):
            x = len(self.tap_dance_entries_available)
            entry = TapDanceEntryUI(x)
            entry.key_changed.connect(self.on_key_changed)
            entry.timing_changed.connect(self.on_timing_changed)
            self.tap_dance_entries_available.append(entry)
            self.cards_available.append(EntryCard(entry.widget()))

    def rebuild_ui(self):
        # the last host_os_count slots are HostOS keys and are edited in the HostOS tab instead
        count = self.keyboard.tap_dance_count - getattr(self.keyboard, "host_os_count", 0)
        self.ensure_entries(count)
        self.tap_dance_entries = self.tap_dance_entries_available[:count]
        self.cards = self.cards_available[:count]
        self.container.set_cards(self.cards)
        self.reload_ui()

    def reload_ui(self):
        for x, e in enumerate(self.tap_dance_entries):
            e.load(self.keyboard.tap_dance_get(x))
        self.update_modified_state()

    def on_save(self):
        for x, e in enumerate(self.tap_dance_entries):
            self.keyboard.tap_dance_set(x, self.tap_dance_entries[x].save())
        self.update_modified_state()
        entry_labels.update(self.keyboard)

    def on_revert(self):
        self.keyboard.reload_dynamic()
        self.reload_ui()

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard
            self.rebuild_ui()

    def valid(self):
        return isinstance(self.device, VialKeyboard) and \
               (self.device.keyboard and self.device.keyboard.vial_protocol >= VIAL_PROTOCOL_DYNAMIC
                and self.device.keyboard.tap_dance_count > 0)

    def on_key_changed(self):
        self.on_save()

    def update_modified_state(self):
        """ Update indication of which cards are modified, and keep Save button enabled only if it's needed """
        has_changes = False
        for x, e in enumerate(self.tap_dance_entries):
            data = e.save()
            title = "TD({})  {}ms".format(x, data[4])
            if data != self.keyboard.tap_dance_get(x):
                has_changes = True
                title += "*"
            self.cards[x].set_title(title)
        self.btn_save.setEnabled(has_changes)

    def on_timing_changed(self):
        self.update_modified_state()
